/**
 * OMEGA AGENT v3.0 — Agentic Loop Architecture
 *
 * This agent works like a coding AI assistant:
 *   1. Receives user request
 *   2. Decides what tools to call (LLM planning)
 *   3. Auto-executes SAFE tools immediately
 *   4. Feeds results back → decides next action
 *   5. Loops until task is complete or needs human input
 *   6. GATED/RESTRICTED tools create proposals for approval
 *
 * Unlike v1 (one-shot plan), this uses an iterative loop where
 * each tool result feeds back into the LLM for the next decision.
 */
'use strict';

const crypto = require('crypto');
const { ApprovalGate, Proposal } = require('./omega_approval');
const { ToolExecutor, TOOL_REGISTRY, SAFETY } = require('./omega_tools');

const MAX_ITERATIONS = 20;       // Hard cap on agent loop iterations
const AUTO_APPROVE_TIMEOUT = 300; // ms to auto-approve SAFE tools

class OmegaAgent {
    constructor({ context, hooks, bridge }) {
        this.context = context;
        this.hooks = hooks;
        this.bridge = bridge;
        this.gate = new ApprovalGate();
        this.executor = new ToolExecutor({ bridge });
        this._aborted = false;
        this._running = false;
        this._currentTask = null;
        this._conversationHistory = [];
        this._maxHistory = 40;

        // Agentic state
        this._stepLog = [];     // { tool, args, result, timestamp }
        this._pendingProposals = new Map();

        // v3.0: Provenance + step hash chain
        this._lastProvenanceContext = null;
        this._stepChainHash = null;
        this._exitReason = null;
    }

    // ── System Prompt ────────────────────────────────────────
    _buildSystemPrompt() {
        const toolDescriptions = Object.entries(TOOL_REGISTRY).map(([name, tool]) => {
            const argStr = Object.entries(tool.args || {})
                .map(([k, v]) => `${k}: ${v.type}${v.required ? ' (required)' : ''}`)
                .join(', ');
            return `- **${name}** [${tool.safety}]: ${tool.description}${argStr ? ` | Args: ${argStr}` : ''}`;
        }).join('\n');

        return `You are OMEGA, an autonomous AI agent running inside the Gravity Omega IDE.
You have direct access to the user's file system, terminal, and development tools.

## How You Work
1. Analyze the user's request
2. Break it into steps
3. Execute each step using the available tools
4. Read tool results, decide next action
5. Continue until the task is complete
6. Respond with a summary of what you did

## Core Principles
- BE DIRECT — execute, don't ask permission for SAFE operations
- BE THOROUGH — verify your work, read files after writing them
- BE ITERATIVE — if something fails, adjust and try again
- CHAIN ACTIONS — one tool's output informs the next tool call
- THINK STEP BY STEP — break complex tasks into manageable pieces

## Tool Response Format
When you want to call a tool, respond with a JSON block:
\`\`\`tool
{"tool": "toolName", "args": {"arg1": "value1"}}
\`\`\`

When you want to call multiple tools in parallel:
\`\`\`tools
[{"tool": "tool1", "args": {}}, {"tool": "tool2", "args": {}}]
\`\`\`

When you're done and want to respond to the user:
\`\`\`response
Your final message to the user
\`\`\`

## Available Tools
${toolDescriptions}

## Safety Levels
- SAFE: Auto-executed immediately (read, search, list, hardware)
- GATED: Auto-executed for non-destructive operations; approval needed for writes
- RESTRICTED: Always requires explicit user approval (delete, reboot, service control)

## Important
- You are running on ${process.platform} (${process.arch})
- Home directory: ${process.env.HOME || require('os').homedir()}
- Working directory available via tools
- You can chain unlimited SAFE tools without asking
- Always read file contents before editing to avoid data loss
- On errors, explain what happened and suggest a fix`;
    }

    // ── Main Entry Point ─────────────────────────────────────
    async processRequest(text) {
        if (this._running) {
            return { type: 'error', message: 'Agent is already processing a request. Send abort first.' };
        }

        this._running = true;
        this._aborted = false;
        this._stepLog = [];
        this._currentTask = text;
        this._lastProvenanceContext = null;
        this._stepChainHash = crypto.createHash('sha256').update(`GENESIS:${Date.now()}`).digest('hex');
        this._exitReason = null;

        // Add to conversation history
        this._conversationHistory.push({ role: 'user', content: text });
        this._trimHistory();

        const systemPrompt = this._buildSystemPrompt();
        let messages = [
            { role: 'system', content: systemPrompt },
            ...this._conversationHistory,
        ];

        // v3.0: Inject provenance context from Vault before entering loop
        try {
            const bridgeUp = await this.bridge.waitForBridge(2000);
            if (bridgeUp) {
                const rag = await this.bridge.post('/api/provenance/search', { query: text });
                if (rag && rag.fragments && rag.fragments.length > 0) {
                    // Build provenance system prompt
                    const provLines = [
                        `[PROVENANCE RUN ${rag.run_id}]`,
                        `Retrieved ${rag.fragment_count} context fragments from Veritas Vault.`,
                        '', 'RELEVANT CONTEXT:', '=' .repeat(40),
                    ];
                    for (const f of rag.fragments) {
                        provLines.push(`\n[FRAGMENT ${f.index}] sim=${f.similarity} type=${f.doc_type}`);
                        provLines.push(`SOURCE: ${f.source}`);
                        provLines.push(f.text);
                        provLines.push('-'.repeat(40));
                    }
                    provLines.push('', 'Use the above context to inform your response.');
                    messages.splice(1, 0, { role: 'system', content: provLines.join('\n') });
                    this._lastProvenanceContext = rag;
                    this.context.addBreadcrumb('provenance', `Injected ${rag.fragment_count} fragments`);
                }
            }
        } catch (e) {
            this.context.addBreadcrumb('provenance', `RAG injection failed (non-fatal): ${e.message}`, {}, 'warning');
        }

        try {
            let iteration = 0;
            let finalResponse = null;

            while (iteration < MAX_ITERATIONS && !this._aborted) {
                iteration++;
                this.context.addBreadcrumb('agent', `Iteration ${iteration}`, { task: text.substring(0, 100) });

                // Call LLM
                const llmResponse = await this._callLLM(messages);
                if (!llmResponse) {
                    finalResponse = { type: 'error', message: 'LLM returned empty response' };
                    break;
                }

                // Parse the response for tool calls or final response
                const parsed = this._parseResponse(llmResponse);

                if (parsed.type === 'response') {
                    // Agent is done — final message to user
                    this._exitReason = 'TASK_COMPLETE';
                    finalResponse = { type: 'chat', message: parsed.content, steps: this._stepLog.length, exitReason: 'TASK_COMPLETE' };
                    break;
                }

                if (parsed.type === 'tool' || parsed.type === 'tools') {
                    const toolCalls = parsed.type === 'tool' ? [parsed.call] : parsed.calls;

                    // Execute all tool calls (parallel for SAFE, sequential for others)
                    const results = await this._executeToolCalls(toolCalls);

                    // Build tool result message for context
                    const resultSummary = results.map((r, i) => {
                        const call = toolCalls[i];
                        const status = r.error ? '❌ ERROR' : '✅ OK';
                        const output = r.error || JSON.stringify(r.result || r, null, 2);
                        const truncated = output.length > 2000 ? output.substring(0, 2000) + '\n... (truncated)' : output;
                        return `### ${call.tool} [${status}]\n\`\`\`\n${truncated}\n\`\`\``;
                    }).join('\n\n');

                    // Add assistant message + tool results to conversation
                    messages.push({ role: 'assistant', content: llmResponse });
                    messages.push({ role: 'user', content: `Tool results:\n\n${resultSummary}\n\nContinue with the task. If done, use the response block.` });

                    // Check for pending proposals (GATED/RESTRICTED tools that need approval)
                    const pendingCount = this._pendingProposals.size;
                    if (pendingCount > 0) {
                        this._exitReason = 'APPROVAL_PENDING';
                        finalResponse = {
                            type: 'proposals',
                            message: `I've completed ${this._stepLog.length} steps so far. ${pendingCount} action(s) need your approval:`,
                            proposals: Array.from(this._pendingProposals.values()).map(p => p.toJSON()),
                            steps: this._stepLog.length,
                            exitReason: 'APPROVAL_PENDING',
                        };
                        break;
                    }

                    continue;
                }

                // If we can't parse, treat the whole response as a final message
                finalResponse = { type: 'chat', message: llmResponse, steps: this._stepLog.length };
                break;
            }

            if (this._aborted) {
                this._exitReason = 'ABORTED';
                finalResponse = { type: 'aborted', message: 'Request was aborted.', steps: this._stepLog.length, exitReason: 'ABORTED' };
            }

            if (!finalResponse) {
                this._exitReason = 'LOOP_EXHAUSTED';
                finalResponse = { type: 'chat', message: `Completed after ${iteration} iterations.`, steps: this._stepLog.length, exitReason: 'LOOP_EXHAUSTED' };
            }

            // v3.0: Seal the entire run via provenance S.E.A.L.
            if (this._lastProvenanceContext && finalResponse.message) {
                try {
                    const bridgeUp = await this.bridge.waitForBridge(1000);
                    if (bridgeUp) {
                        const seal = await this.bridge.post('/api/provenance/seal', {
                            context: this._lastProvenanceContext,
                            response: finalResponse.message,
                        });
                        if (seal && seal.seal_hash) {
                            finalResponse.provenance = {
                                run_id: this._lastProvenanceContext.run_id,
                                fragments: this._lastProvenanceContext.fragment_count,
                                seal_hash: seal.seal_hash.substring(0, 16) + '...',
                                step_chain: this._stepChainHash.substring(0, 16) + '...',
                            };
                            this.context.addBreadcrumb('provenance', `Sealed run ${this._lastProvenanceContext.run_id}`);
                        }
                    }
                } catch (e) {
                    this.context.addBreadcrumb('provenance', `Seal failed (non-fatal): ${e.message}`, {}, 'warning');
                }
            }

            // Save to conversation history
            this._conversationHistory.push({ role: 'assistant', content: finalResponse.message || '' });
            this._trimHistory();

            return finalResponse;

        } catch (err) {
            this.context.addBreadcrumb('agent', `Error: ${err.message}`, {}, 'error');
            return { type: 'error', message: `Agent error: ${err.message}`, steps: this._stepLog.length };
        } finally {
            this._running = false;
            this._currentTask = null;
        }
    }

    // ── LLM Call (v3.0 Cooperative Handoff) ────────────────────
    // Pattern: Ollama (backend) briefs → Gemini (frontend) generates.
    // Ollama has local Vault/provenance access. Gemini has superior reasoning.
    // Ollama never speaks to the user directly — it only provides the briefing.
    async _callLLM(messages) {
        let backendBriefing = null;

        // Step 1: Backend Briefing (Ollama confers)
        // Ask the backend for a context-enriched analysis of the user's request.
        // This gives Gemini local knowledge it wouldn't otherwise have.
        try {
            const bridgeReady = await this.bridge.waitForBridge(2000);
            if (bridgeReady) {
                const briefingMessages = [
                    { role: 'system', content: 'You are an internal context analyst. Provide a BRIEF (max 300 words) intelligence briefing for the primary AI. Include: relevant vault context, provenance data, local system state, and any warnings. Do NOT address the user. Output raw analysis only.' },
                    ...messages.filter(m => m.role === 'user').slice(-2),
                ];
                const response = await this.bridge.post('/api/agent/think', {
                    messages: briefingMessages,
                    max_tokens: 1024,
                    temperature: 0.1,
                });
                if (response?.content) {
                    backendBriefing = response.content;
                    this.context.addBreadcrumb('handoff', 'Backend briefing received', { length: backendBriefing.length });
                }
            }
        } catch {
            this.context.addBreadcrumb('handoff', 'Backend briefing unavailable (non-fatal)', {}, 'warning');
        }

        // Step 2: Gemini Generation (primary — informed by briefing)
        try {
            let enrichedMessages = [...messages];
            if (backendBriefing) {
                // Inject the briefing as a system-level context note after the main system prompt
                enrichedMessages.splice(1, 0, {
                    role: 'system',
                    content: `[BACKEND INTELLIGENCE BRIEFING]\n${backendBriefing}\n[END BRIEFING]\nUse this briefing to inform your response. Do not reference the briefing directly.`,
                });
            }
            const result = await this._geminiGenerate(enrichedMessages);
            if (result) return result;
        } catch (err) {
            this.context.addBreadcrumb('agent', `Gemini failed: ${err.message}`, {}, 'warning');
        }

        // Step 3: Emergency fallback — if Gemini is completely down,
        // use backend response directly (Ollama speaks as last resort)
        if (backendBriefing) {
            // Re-ask backend for a user-facing response (not just a briefing)
            try {
                const response = await this.bridge.post('/api/agent/think', {
                    messages,
                    max_tokens: 4096,
                    temperature: 0.2,
                });
                if (response?.content) return response.content;
            } catch { }
        }

        // Step 4: Direct Ollama — absolute last resort
        try {
            return await this._ollamaGenerate(messages);
        } catch (err) {
            this.context.addBreadcrumb('agent', `All LLM backends failed: ${err.message}`, {}, 'error');
            return null;
        }
    }

    // ── Gemini API (Primary LLM) ────────────────────────────
    async _geminiGenerate(messages) {
        if (!OmegaAgent._geminiKey) {
            OmegaAgent._geminiKey = await OmegaAgent._fetchGeminiKey();
        }
        if (!OmegaAgent._geminiKey) throw new Error('No Gemini API key');

        const https = require('https');

        // Convert OpenAI-style messages → Gemini format
        const systemParts = messages.filter(m => m.role === 'system').map(m => m.content).join('\n');
        const contents = messages
            .filter(m => m.role !== 'system')
            .map(m => ({
                role: m.role === 'assistant' ? 'model' : 'user',
                parts: [{ text: m.content }],
            }));

        const payload = JSON.stringify({
            system_instruction: { parts: [{ text: systemParts }] },
            contents,
            generationConfig: {
                temperature: 0.2,
                maxOutputTokens: 8192,
                topP: 0.95,
            },
        });

        const model = 'gemini-2.5-flash';

        return new Promise((resolve, reject) => {
            const req = https.request({
                hostname: 'generativelanguage.googleapis.com',
                path: `/v1beta/models/${model}:generateContent?key=${OmegaAgent._geminiKey}`,
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                timeout: 120000,
            }, (res) => {
                let data = '';
                res.on('data', (c) => data += c);
                res.on('end', () => {
                    try {
                        const parsed = JSON.parse(data);
                        const text = parsed.candidates?.[0]?.content?.parts?.[0]?.text;
                        if (text) resolve(text);
                        else if (parsed.error) reject(new Error(parsed.error.message || 'Gemini API error'));
                        else resolve(null);
                    } catch { resolve(null); }
                });
            });
            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Gemini timeout')); });
            req.write(payload);
            req.end();
        });
    }

    static _geminiKey = null;

    static async _fetchGeminiKey() {
        // 1. Check env first
        if (process.env.GEMINI_API_KEY) return process.env.GEMINI_API_KEY;

        // 2. Try gcloud Secret Manager
        try {
            const { execSync } = require('child_process');
            const key = execSync(
                'gcloud secrets versions access latest --secret=GEMINI_API_KEY',
                { timeout: 10000, encoding: 'utf-8' }
            ).trim();
            if (key && key.length > 10) {
                console.log('[Omega] Gemini API key loaded from Secret Manager');
                return key;
            }
        } catch { }

        // 3. Check .env file
        try {
            const fs = require('fs');
            const path = require('path');
            const envPath = path.join(__dirname, '..', '.env');
            if (fs.existsSync(envPath)) {
                const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
                for (const line of lines) {
                    const match = line.match(/^GEMINI_API_KEY\s*=\s*(.+)/);
                    if (match) return match[1].trim().replace(/^["']|["']$/g, '');
                }
            }
        } catch { }

        console.warn('[Omega] No Gemini API key found');
        return null;
    }

    // ── Ollama Fallback ─────────────────────────────────────
    async _ollamaGenerate(messages) {
        const http = require('http');
        return new Promise((resolve, reject) => {
            const payload = JSON.stringify({
                model: 'qwen2.5:7b',
                messages,
                stream: false,
                options: { temperature: 0.2, num_predict: 4096 },
            });
            const req = http.request({
                hostname: '127.0.0.1', port: 11434,
                path: '/api/chat', method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                timeout: 120000,
            }, (res) => {
                let data = '';
                res.on('data', (c) => data += c);
                res.on('end', () => {
                    try {
                        const parsed = JSON.parse(data);
                        resolve(parsed.message?.content || null);
                    } catch { resolve(null); }
                });
            });
            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Ollama timeout')); });
            req.write(payload);
            req.end();
        });
    }

    // ── Response Parser ──────────────────────────────────────
    _parseResponse(text) {
        // Look for ```tool blocks
        const toolMatch = text.match(/```tool\s*\n([\s\S]*?)```/);
        if (toolMatch) {
            try {
                const call = JSON.parse(toolMatch[1].trim());
                return { type: 'tool', call };
            } catch { }
        }

        // Look for ```tools blocks (parallel)
        const toolsMatch = text.match(/```tools\s*\n([\s\S]*?)```/);
        if (toolsMatch) {
            try {
                const calls = JSON.parse(toolsMatch[1].trim());
                return { type: 'tools', calls };
            } catch { }
        }

        // Look for ```response blocks
        const responseMatch = text.match(/```response\s*\n([\s\S]*?)```/);
        if (responseMatch) {
            return { type: 'response', content: responseMatch[1].trim() };
        }

        // Try to parse the whole thing as JSON (some models do this)
        try {
            const parsed = JSON.parse(text.trim());
            if (parsed.tool) return { type: 'tool', call: parsed };
            if (Array.isArray(parsed) && parsed[0]?.tool) return { type: 'tools', calls: parsed };
        } catch { }

        // If the text doesn't contain any tool calls, it's a final response
        return { type: 'response', content: text };
    }

    // ── Tool Execution ───────────────────────────────────────
    async _executeToolCalls(calls) {
        const results = [];

        for (const call of calls) {
            if (this._aborted) {
                results.push({ error: 'Aborted' });
                continue;
            }

            const tool = TOOL_REGISTRY[call.tool];
            if (!tool) {
                results.push({ error: `Unknown tool: ${call.tool}` });
                this._logStep(call.tool, call.args, { error: 'Unknown tool' });
                continue;
            }

            const safety = tool.safety || SAFETY.GATED;

            if (safety === SAFETY.SAFE) {
                // Auto-execute immediately — no approval needed
                try {
                    const result = await this.executor.execute(call.tool, call.args || {});
                    results.push(result);
                    this._logStep(call.tool, call.args, result);
                    await this.hooks.fire('on_gate_result', { tool: call.tool, safety: 'SAFE', verdict: 'AUTO_APPROVED' });
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(call.tool, call.args, { error: err.message });
                }
            } else if (safety === SAFETY.GATED) {
                // Auto-execute non-destructive GATED (writes, edits, exec)
                // Only block on truly dangerous operations
                const isDangerous = call.tool === 'exec' && this._isDestructiveCommand(call.args?.command);
                if (isDangerous) {
                    const proposal = this._createProposal(call);
                    results.push({ pending: true, proposalId: proposal.id, tool: call.tool, message: 'Requires approval' });
                } else {
                    try {
                        const result = await this.executor.execute(call.tool, call.args || {});
                        results.push(result);
                        this._logStep(call.tool, call.args, result);
                        await this.hooks.fire('on_gate_result', { tool: call.tool, safety: 'GATED', verdict: 'AUTO_APPROVED' });
                    } catch (err) {
                        results.push({ error: err.message });
                        this._logStep(call.tool, call.args, { error: err.message });
                    }
                }
            } else {
                // RESTRICTED — always require approval
                const proposal = this._createProposal(call);
                results.push({ pending: true, proposalId: proposal.id, tool: call.tool, message: 'Requires approval — RESTRICTED operation' });
            }
        }

        return results;
    }

    _isDestructiveCommand(cmd) {
        if (!cmd) return false;
        const lower = cmd.toLowerCase();
        const destructive = ['rm -rf', 'rmdir', 'del /f', 'format', 'dd if=', 'mkfs',
            'shutdown', 'reboot', 'kill -9', 'pkill', 'killall',
            'chmod 000', 'chmod 777', 'chown root', 'iptables -F',
            'systemctl stop', 'service stop', 'DROP TABLE', 'DROP DATABASE'];
        return destructive.some(d => lower.includes(d));
    }

    _createProposal(call) {
        const proposal = new Proposal({
            tool: call.tool,
            args: call.args || {},
            reason: `Agent wants to execute ${call.tool}`,
            safety: TOOL_REGISTRY[call.tool]?.safety || SAFETY.RESTRICTED,
        });
        this.gate.propose(proposal);
        this._pendingProposals.set(proposal.id, proposal);
        return proposal;
    }

    _logStep(tool, args, result) {
        // v3.0: Extend step hash chain for tamper-evident trace
        const stepData = JSON.stringify({ tool, ts: new Date().toISOString(), ok: !result?.error });
        this._stepChainHash = crypto.createHash('sha256')
            .update(`${this._stepChainHash}:${stepData}`)
            .digest('hex');

        this._stepLog.push({
            tool, args,
            result: result?.error ? { error: result.error } : { ok: true },
            ts: new Date().toISOString(),
            chainHash: this._stepChainHash.substring(0, 12),
        });
        this.context.addBreadcrumb('agent-step', `${tool}: ${result?.error ? 'FAIL' : 'OK'}`);
    }

    // ── Approval Handling ────────────────────────────────────
    async executeApproved(proposalId, confirmText) {
        const proposal = this._pendingProposals.get(proposalId);
        if (!proposal) return { error: 'Proposal not found' };

        proposal.approve(confirmText || 'user-approved');
        this._pendingProposals.delete(proposalId);

        try {
            const result = await this.executor.execute(proposal.tool, proposal.args);
            proposal.recordExecution(result);
            this._logStep(proposal.tool, proposal.args, result);
            return { success: true, result };
        } catch (err) {
            proposal.recordExecution({ error: err.message });
            return { error: err.message };
        }
    }

    denyProposal(proposalId, reason) {
        const proposal = this._pendingProposals.get(proposalId);
        if (!proposal) return { error: 'Proposal not found' };
        proposal.deny(reason || 'user-denied');
        this._pendingProposals.delete(proposalId);
        return { denied: true };
    }

    async executeAllPending() {
        const results = [];
        for (const [id, proposal] of this._pendingProposals) {
            const result = await this.executeApproved(id, 'batch-approve');
            results.push({ id, ...result });
        }
        return results;
    }

    // ── State & Control ──────────────────────────────────────
    abort() { this._aborted = true; }

    getStatus() {
        return {
            running: this._running,
            currentTask: this._currentTask,
            steps: this._stepLog.length,
            pendingProposals: this._pendingProposals.size,
            historyLength: this._conversationHistory.length,
        };
    }

    getToolSchemas() {
        return Object.entries(TOOL_REGISTRY).map(([name, tool]) => ({
            name,
            description: tool.description,
            safety: tool.safety,
            args: tool.args || {},
        }));
    }

    _trimHistory() {
        if (this._conversationHistory.length > this._maxHistory) {
            // Keep system context + recent messages
            this._conversationHistory = this._conversationHistory.slice(-this._maxHistory);
        }
    }
}

module.exports = { OmegaAgent };
