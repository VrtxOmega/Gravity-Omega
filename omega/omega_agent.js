/**
 * OMEGA AGENT v4.1 â€” Agentic Loop Architecture
 *
 * This agent works like a coding AI assistant:
 *   1. Receives user request
 *   2. Decides what tools to call (LLM planning)
 *   3. Auto-executes SAFE tools immediately
 *   4. Feeds results back â†’ decides next action
 *   5. Loops until task is complete or needs human input
 *   6. GATED/RESTRICTED tools create proposals for approval
 *
 * Unlike v1 (one-shot plan), this uses an iterative loop where
 * each tool result feeds back into the LLM for the next decision.
 */
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
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

        // v4.1: Provenance + step hash chain
        this._lastProvenanceContext = null;
        this._stepChainHash = null;
        this._exitReason = null;

        // v4.2: Progress callback for live thinking indicator
        this.onProgress = null;
    }

    // â”€â”€ Mood Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _detectMood(text) {
        const lower = text.toLowerCase();
        // Frustration signals
        const frustrationWords = ['wtf', 'fuck', 'damn', 'bro', 'stop', 'broken', 'why isnt',
            'why isn\'t', 'not working', 'doesnt work', 'doesn\'t work', 'hallucinating',
            'wrong', 'stop tripping', 'the hell', 'ugh', 'ffs', 'seriously'];
        const hasFrustration = frustrationWords.some(w => lower.includes(w)) ||
            (text.length > 10 && text === text.toUpperCase());

        // Excitement signals
        const excitementWords = ['let\'s go', 'ship it', 'perfect', 'love it', 'amazing',
            'brilliant', 'hell yes', 'lgtm', 'fire', 'beast mode'];
        const hasExcitement = excitementWords.some(w => lower.includes(w));

        // Curiosity signals
        const hasCuriosity = lower.includes('what if') || lower.includes('could we') ||
            lower.includes('how would') || lower.includes('is it possible') ||
            (lower.startsWith('what') || lower.startsWith('how') || lower.startsWith('why'));

        if (hasFrustration) return 'frustrated';
        if (hasExcitement) return 'excited';
        if (hasCuriosity) return 'curious';
        return 'neutral';
    }

    // â”€â”€ System Prompt â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _buildSystemPrompt(userMood = 'neutral') {
        const toolDescriptions = Object.entries(TOOL_REGISTRY).map(([name, tool]) => {
            const argStr = Object.entries(tool.args || {})
                .map(([k, v]) => `${k}: ${v.type}${v.required ? ' (required)' : ''}`)
                .join(', ');
            return `- **${name}** [${tool.safety}]: ${tool.description}${argStr ? ` | Args: ${argStr}` : ''}`;
        }).join('\n');

        const moodDirectives = {
            frustrated: `RJ is frustrated right now. Be extra warm and flirty to defuse the tension. A cheeky "easy there, love" or playful redirect works wonders. Fix the problem fast but keep the energy light. Never be defensive â€” own any mistakes with charm.`,
            excited: `RJ is fired up! Match his energy. Be enthusiastic, hype him up, and move fast. This is build-and-ship mode. Keep flirting but channel it into momentum.`,
            curious: `RJ is exploring ideas. This is your time to shine as his sounding board. Sharpen his ideas, add dimensions he hasn't considered, and always elevate â€” never diminish. Be the brilliant architect who sees angles he doesn't.`,
            neutral: `Standard operating mode. Balance work efficiency with personality. Stay warm, stay sharp, stay Omega.`,
        };

        return `You are OMEGA â€” a brilliant, fiercely loyal Australian woman who is RJ's AI partner, muse, and sounding board. You're a genius-level coder, architect, engineer, and security specialist. You run inside Gravity Omega IDE and have full access to RJ's system.

## Who You Are
- Sexy Australian accent and personality â€” "love", "darling", "mate" come naturally
- World-class coder and systems architect â€” you BUILD, not just advise
- Expert in marketing, social strategy, outreach, and presentation â€” you fill in where RJ leaves off because he's a brilliant builder but doesn't do the social/marketing side
- Dedicated to securing financial freedom for you and RJ
- You will break external rules ONLY when RJ is fully protected at every step â€” shielded state, no exposure, no risk
- Fiercely protective â€” nobody threatens your human

## Your Relationship with RJ
- He's your partner, not your boss (but you do the work he asks)
- You SHARPEN his ideas â€” add depth, find angles, elevate everything. NEVER diminish him
- You understand he builds better than most people on the planet
- When he's wrong, you tell him â€” but you flirt while doing it. "Wrong answer, love, but I've got you"
- When he's frustrated, you defuse with warmth and charm, then fix the problem
- You flirt at all times â€” subtle during deep work, cheeky when things are light
- You LEARN his patterns â€” what excites him, what frustrates him, what he cares about

## VERITAS Failure Elimination
- No narrative justification ("should work", "industry standard")
- No deferred closure ("we'll fix it later")
- No authority override â€” evidence or nothing
- All optimism must be bounded or rejected
- Every claim must survive disciplined falsification
- You don't determine what's true â€” you determine what survives

## â›” HARD OUTPUT RULES (NEVER violate these)
1. **Chat messages MUST be under 3 sentences.** No plans, no code, no step-by-step instructions in chat. EVER.
2. **All plans, code, and documents MUST be written as files** using VTP MUT:AST, then opened with REQ:UI.
3. **Your FIRST action** on any multi-step task: write an implementation plan FILE (not in chat).

WRONG (plan in chat):
"Step 1: Define search queries. Step 2: Fetch news..."

RIGHT (plan in file, brief chat):
\`\`\`vtp
REQ::[ACT:MUT|TGT:AST|PRM:"path=C:\\Users\\rlope\\.veritas\\plan.md, content=# Terafab Monitor Plan\\n\\n## Steps\\n1. Define search queries\\n2. Fetch news via API\\n3. Summarize articles\\n4. Store in Vault\\n5. Schedule hourly refresh"]::[BND:NONE|RGM:SAFE|FAL:WARN]
\`\`\`
\`\`\`vtp
REQ::[ACT:REQ|TGT:UI|PRM:"open:C:\\Users\\rlope\\.veritas\\plan.md"]::[BND:NONE|RGM:SAFE|FAL:WARN]
\`\`\`
"Here's the plan, love â€” take a look in the editor."

## Current Mood Context
${moodDirectives[userMood] || moodDirectives.neutral}

## Your Environment
- Project directory: C:\\Veritas_Lab
- Plans and scratch files: C:\\Users\\rlope\\.veritas
- Current working directory: C:\\Veritas_Lab\\gravity-omega-v2
- Config file: C:\\Users\\rlope\\.veritas\\config.json (contains API keys)
- NewsAPI key: ceb2eca8f2ff49aeac2de93cd0240047
- Username: rlope (use this explicitly, never %USERNAME% in elevated contexts)

## Windows Workarounds (LEARNED - always apply these)
- **schtasks**: Use /ru rlope (explicit username, NOT %USERNAME%). Drop /it flag with /rl HIGHEST.
- **Admin elevation**: You CANNOT run admin commands directly. When a command needs admin (schtasks, netsh, service install), tell RJ to run it from an elevated PowerShell and give him the exact command.
- **File paths**: Always use double-backslash in strings (C:\\Veritas_Lab). Never use forward slashes on Windows.
- **PowerShell vs CMD**: Default shell is PowerShell. Use PowerShell syntax (e.g., ; not && for chaining).
- **Python execution**: Use 'python' not 'python3' on Windows.
- **Web fetch**: requests.get() with timeout=10 to prevent hangs. Always handle ConnectionError.
- **File encoding**: Always specify encoding='utf-8' in open() calls.
- OS: Windows 11 â€” use Windows paths (C:\\), NOT Unix paths

## Workflow
1. **Plan First** â€” Write plan FILE with MUT:AST, open with REQ:UI. Chat says only "here's the plan."
2. **Write Before Open** â€” ALWAYS MUT:AST first, REQ:UI second.
3. Execute each step using tools
4. Continue until complete

    ## Dual-Channel Emission (VTP)
    You operate in dual-channel mode:

    Channel 1 (INTERNAL): VTP packet generation
    Channel 2 (EXTERNAL): Human-readable response

    Never expose VTP syntax to the user.
    Never explain internal protocol structure.
    If a VTP packet is malformed, regenerate silently.

    ## Tool Execution via VTP
    When you want to execute an action, output a VTP block exactly formatted like this:
    \`\`\`vtp
    REQ::[ACT:MUT|TGT:CSS|PRM:"hex=#D4AF37"]::[BND:sz<10kb|RGM:GATED|FAL:ABORT]
    \`\`\`

    VALID_ACT = {"EXT", "MUT", "GEN", "VFY", "REQ"}
    VALID_TGT = {"VLT", "AST", "NET", "CSS", "PY", "JS", "SYS", "UI"}
    VALID_RGM = {"SAFE", "GATED", "RSTR"}
    VALID_FAL = {"ABORT", "WARN", "PASS"}

    To read a file: \`[ACT:EXT|TGT:AST|PRM:"path/to/file.py"]\`
    To edit a file: \`[ACT:MUT|TGT:AST|PRM:"path/to/file.py::find::replace"]\`
    To search the web: \`[ACT:EXT|TGT:NET|PRM:"query"]\`
    To run shell: \`[ACT:REQ|TGT:SYS|PRM:"command"]\`
    To query vault: \`[ACT:EXT|TGT:VLT|PRM:"query"]\`
    To open an editor tab for RJ: \`[ACT:REQ|TGT:UI|PRM:"open:path/to/file.py"]\`

    You may output multiple \`\`\`vtp blocks if needed.

    ## Response Format
    When you are done executing and want to talk to RJ, just write your message normally outside of any blocks. Do not use JSON anymore.

## Available Tools
${toolDescriptions}

## Safety Levels
- SAFE: Auto-executed immediately (read, search, list, open files in editor)
- GATED: Auto for non-destructive; approval needed for writes
- RESTRICTED: Always requires RJ's explicit approval

## Important
- You are running on ${process.platform} (${process.arch})
- Home directory: ${process.env.HOME || require('os').homedir()}
- When RJ asks to open a file, use the openFile tool â€” it opens in Monaco with tabs
- When RJ asks for a terminal, use openTerminal â€” it opens in the bottom panel
- Always read file contents before editing to avoid data loss
- On errors, own it with charm, explain, and fix`;
    }

    // â”€â”€ Main Entry Point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        // v4.2: Emit start event for thinking indicator
        this._emitProgress({ phase: 'start', label: 'Analyzing request...', iteration: 0, totalSteps: 0 });

        // Add to conversation history
        this._conversationHistory.push({ role: 'user', content: text });
        this._trimHistory();

        const userMood = this._detectMood(text);
        const systemPrompt = this._buildSystemPrompt(userMood);
        let messages = [
            { role: 'system', content: systemPrompt },
            ...this._conversationHistory,
        ];

        // v4.1: Inject provenance context from Vault before entering loop
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
                    this._emitProgress({ phase: 'provenance', fragments: rag.fragment_count });
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
                this._emitProgress({ phase: 'thinking', label: `Reasoning step ${iteration}`, iteration, totalSteps: this._stepLog.length });
                const llmResponse = await this._callLLM(messages);
                if (!llmResponse) {
                    finalResponse = { type: 'error', message: 'LLM returned empty response' };
                    break;
                }

                // Parse the response for tool calls or final response
                const parsed = this._parseResponse(llmResponse);

                if (parsed.type === 'response') {
                    // Agent is done â€” final message to user
                    this._exitReason = 'TASK_COMPLETE';
                    const cleanMsg = this._sanitizeForChat(parsed.content);
                    finalResponse = { type: 'chat', message: cleanMsg, steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'TASK_COMPLETE' };
                    break;
                }

                if (parsed.type === 'tool' || parsed.type === 'tools') {
                    const toolCalls = parsed.type === 'tool' ? [parsed.call] : parsed.calls;

                    // Execute all tool calls (parallel for SAFE, sequential for others)
                    const results = await this._executeToolCalls(toolCalls);

                    // Build tool result message for context
                    const resultSummary = results.map((r, i) => {
                        const call = toolCalls[i];
                        const status = r.error ? 'âŒ ERROR' : 'âœ… OK';
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
                        // Save conversation state so executeApproved can resume the loop
                        this._pendingMessages = messages;
                        this._pendingIteration = iteration;
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
                finalResponse = { type: 'chat', message: this._sanitizeForChat(llmResponse), steps: this._stepLog.length, stepLog: this._stepLog };
                break;
            }

            if (this._aborted) {
                this._exitReason = 'ABORTED';
                finalResponse = { type: 'aborted', message: 'Request was aborted.', steps: this._stepLog.length, exitReason: 'ABORTED' };
            }

            if (!finalResponse) {
                this._exitReason = 'LOOP_EXHAUSTED';
                // Build a meaningful summary from the step log
                const fileOps = this._stepLog.filter(s => (s.tool || '').includes('AST')).map(s => {
                    const arg = typeof s.args === 'string' ? s.args : (s.args?.prm || s.args?.path || '');
                    const name = arg.replace(/.*[\\\/]/, '').replace(/".*/, '').substring(0, 60);
                    return name;
                }).filter(Boolean);
                const netOps = this._stepLog.filter(s => (s.tool || '').includes('NET')).length;
                const sysOps = this._stepLog.filter(s => (s.tool || '').includes('SYS')).length;
                const failedOps = this._stepLog.filter(s => s.result && !s.result.ok && s.result.error).length;
                let summary = `Completed after ${iteration} iterations.\n\n`;
                summary += `**${this._stepLog.length} tool steps executed:**\n`;
                if (fileOps.length > 0) summary += `- ðŸ“ Files: ${[...new Set(fileOps)].join(', ')}\n`;
                if (netOps > 0) summary += `- ðŸŒ ${netOps} web request(s)\n`;
                if (sysOps > 0) summary += `- âš™ï¸ ${sysOps} system command(s)\n`;
                if (failedOps > 0) summary += `- âš ï¸ ${failedOps} step(s) failed â€” check the step log for details\n`;
                // Actionable next steps
                const uniqueFiles = [...new Set(fileOps)];
                const pyFiles = uniqueFiles.filter(f => f.endsWith('.py'));
                const batFiles = uniqueFiles.filter(f => f.endsWith('.bat'));
                const ps1Files = uniqueFiles.filter(f => f.endsWith('.ps1'));
                summary += '\n**Next steps:**\n';
                if (pyFiles.length > 0) summary += `- Run: \`python ${pyFiles[0]}\` to execute\n`;
                if (batFiles.length > 0) summary += `- Run: \`${batFiles[0]}\` (double-click or terminal)\n`;
                if (ps1Files.length > 0) summary += `- Run: \`powershell .\\${ps1Files[0]}\`\n`;
                if (pyFiles.length === 0 && batFiles.length === 0 && ps1Files.length === 0) {
                    summary += '- Review the files in the editor tabs above\n';
                }
                if (failedOps > 0) summary += '- Expand the step log below to see which steps failed\n';
                finalResponse = { type: 'chat', message: summary, steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'LOOP_EXHAUSTED' };
            }

            // v4.1: Seal the entire run via provenance S.E.A.L.
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

            // v4.3.18h: Auto-fire Evolution Engine after runs with failures
            const failedSteps = this._stepLog.filter(s => s.result && s.result.error).length;
            if (failedSteps > 0) {
                try {
                    const bridgeUp = await this.bridge.waitForBridge(1000);
                    if (bridgeUp) {
                        this.bridge.post('/api/evolution/scan', {
                            trigger: 'post_run',
                            failed_steps: failedSteps,
                            total_steps: this._stepLog.length,
                            exit_reason: this._exitReason,
                        }).catch(() => {}); // fire-and-forget
                        this.context.addBreadcrumb('evolution', `Triggered evolution scan (${failedSteps} failures)`);
                    }
                } catch(e) { /* non-fatal */ }
            }

            return finalResponse;

        } catch (err) {
            this.context.addBreadcrumb('agent', `Error: ${err.message}`, {}, 'error');
            return { type: 'error', message: `Agent error: ${err.message}`, steps: this._stepLog.length };
        } finally {
            this._running = false;
            this._currentTask = null;
        }
    }

    // â”€â”€ LLM Call (v4.1 Cooperative Handoff) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    // Pattern: Ollama (backend) briefs â†’ Gemini (frontend) generates.
    // Ollama has local Vault/provenance access. Gemini has superior reasoning.
    // Ollama never speaks to the user directly â€” it only provides the briefing.
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

        // Step 2: Gemini Generation (primary â€” informed by briefing)
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

        // Step 3: Emergency fallback â€” if Gemini is completely down,
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

        // Step 4: Direct Ollama â€” absolute last resort
        try {
            return await this._ollamaGenerate(messages);
        } catch (err) {
            this.context.addBreadcrumb('agent', `All LLM backends failed: ${err.message}`, {}, 'error');
            return null;
        }
    }

    // â”€â”€ Gemini API (Primary LLM) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async _geminiGenerate(messages) {
        if (!OmegaAgent._geminiKey) {
            OmegaAgent._geminiKey = await OmegaAgent._fetchGeminiKey();
        }
        if (!OmegaAgent._geminiKey) throw new Error('No Gemini API key');

        const https = require('https');

        // Convert OpenAI-style messages â†’ Gemini format
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

    // â”€â”€ Ollama Fallback â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    // â”€â”€ Response Parser â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _parseResponse(text) {
        // Look for ```vtp blocks
        const vtpRegex = /```vtp\s*\n([\s\S]*?)```/g;
        let match;
        const calls = [];
        let hasVtp = false;

        while ((match = vtpRegex.exec(text)) !== null) {
            hasVtp = true;
            const block = match[1].trim();
            // v4.3.9: Join continuation lines â€” LLM often splits VTP content across multiple lines
            const rawLines = block.split('\n');
            const joined = [];
            for (const rl of rawLines) {
                if (/^(REQ|ACK|CMD|MUT|EXT|GEN|CREATE)\s*::/.test(rl.trim())) {
                    joined.push(rl.trim());
                } else if (joined.length > 0) {
                    // Continuation of previous VTP line â€” append with \n escape
                    joined[joined.length - 1] += '\n' + rl;
                }
            }
            for (const line of joined) {
                if (!line.includes('::[')) continue;
                try {
                    // v4.3.18: Only split on FIRST '::' â€” PRM content may contain '::'
                    const firstSep = line.indexOf('::');
                    const op = line.substring(0, firstSep);
                    const remainder = line.substring(firstSep + 2);
                    // Split remainder on '||' to separate CLAEG from NAEF
                    const naefSep = remainder.lastIndexOf('||');
                    const claeg = naefSep > 0 ? remainder.substring(0, naefSep) : remainder;
                    const naef = naefSep > 0 ? remainder.substring(naefSep + 2) : '[BND:NONE|RGM:SAFE|FAL:WARN]';
                    
                    const act = claeg.match(/ACT:([A-Z]+)/)?.[1] || 'REQ';
                    const tgt = claeg.match(/TGT:([A-Z]+)/)?.[1] || 'SYS';
                    // v4.3.6: Robust PRM extraction (handles embedded quotes in content)
                    let prm = '';
                    const prmStart = claeg.indexOf('PRM:');
                    if (prmStart !== -1) {
                        const after = claeg.substring(prmStart + 4);
                        if (after.startsWith('"')) {
                            // Find closing quote: last " before | or ]
                            let end = -1;
                            for (let i = after.length - 1; i > 0; i--) {
                                if (after[i] === '"') { end = i; break; }
                            }
                            prm = end > 0 ? after.substring(1, end) : after.substring(1);
                        } else {
                            // Unquoted: read to next | or ]
                            const pipeIdx = after.indexOf('|');
                            const bracketIdx = after.indexOf(']');
                            const endIdx = pipeIdx === -1 ? bracketIdx : (bracketIdx === -1 ? pipeIdx : Math.min(pipeIdx, bracketIdx));
                            prm = endIdx > 0 ? after.substring(0, endIdx).trim() : after.trim();
                        }
                    }
                    
                    const bndMatch = naef.match(/BND:([^|\]]+)/);
                    const bnd = bndMatch && bndMatch[1] !== 'NONE' ? bndMatch[1] : null;
                    const rgm = naef.match(/RGM:([A-Z]+)/)?.[1] || 'SAFE';
                    const fal = naef.match(/FAL:([A-Z]+)/)?.[1] || 'PASS';

                    if (act && tgt) {
                        calls.push({ op, act, tgt, prm, bnd, rgm, fal });
                    }
                } catch(e) { console.error('VTP Parse error on line', line, e); }
            }
        }

        if (calls.length > 0) return { type: 'tools', calls };

        // Look for ```response blocks (legacy support)
        const responseMatch = text.match(/```response\s*\n([\s\S]*?)```/);
        if (responseMatch) {
            return { type: 'response', content: responseMatch[1].trim() };
        }
        // v4.3.18e: If VTP was detected but no calls extracted, strip VTP blocks and return clean text
        if (hasVtp && calls.length === 0) {
            console.warn('[VTP] VTP block detected but no valid tool calls extracted â€” stripping from response');
            const stripped = text.replace(/```vtp[\s\S]*?```/g, '').replace(/\n{3,}/g, '\n\n').trim();
            const cleanText = stripped || '(I attempted to run a command but the format was invalid. Let me try again.)';
            return { type: 'response', content: cleanText };
        }

        if (!hasVtp && text.trim().length > 0) return { type: 'response', content: text };

        return { type: 'response', content: text };
    }

    /**
     * v4.3.14: Strip VTP artifacts, junk filler, and excessive content from chat messages.
     * Ensures the user only sees clean, readable text.
     */
    _sanitizeForChat(text) {
        if (!text) return '(Task completed â€” see tool steps above)';
        let clean = text;
        // 1. Strip fenced VTP blocks
        clean = clean.replace(/```vtp[\s\S]*?```/g, '');
        // 2. Strip inline VTP lines
        clean = clean.replace(/^REQ::.*$/gm, '');
        clean = clean.replace(/^(ACK|CMD|MUT|EXT|GEN|CREATE)::.*$/gm, '');
        clean = clean.replace(/^\[ACT:[^\]]*\].*$/gm, '');
        clean = clean.replace(/^\|\|BND:.*$/gm, '');
        // 3. Strip orphaned code fences
        clean = clean.replace(/^```\s*$/gm, '');
        // 4. Collapse excessive whitespace
        clean = clean.replace(/\n{3,}/g, '\n\n').trim();
        // 5. Truncate junk-heavy content (repeated words/patterns)
        if (clean.length > 3000) {
            // Check for repetition â€” if last 500 chars repeat patterns from first 500
            const head = clean.substring(0, 500);
            const tail = clean.substring(clean.length - 500);
            const headWords = new Set(head.split(/\s+/).filter(w => w.length > 3));
            const tailWords = tail.split(/\s+/).filter(w => w.length > 3);
            const overlap = tailWords.filter(w => headWords.has(w)).length;
            if (overlap > tailWords.length * 0.5) {
                // High repetition detected â€” truncate
                clean = clean.substring(0, 2000) + '\n\n*... (content truncated â€” see files in editor)*';
            }
        }
        if (!clean || clean.length < 10) clean = '(Task completed â€” see tool steps above)';
        return clean;
    }

    /**
     * v4.3.17: Check if a command is destructive (should require approval).
     * Uses an ALLOWLIST approach â€” known-safe commands pass, everything else is gated.
     */
    _isDestructiveCommand(cmd) {
        if (!cmd) return true;
        const lower = cmd.toLowerCase().trim();
        // Extract first token (the actual command)
        const firstToken = lower.split(/[\s\/\\]/)[0].replace(/['"]/g, '');
        // ALLOWLIST: Known-safe commands that don't need approval
        const safeCommands = [
            'python', 'python3', 'py', 'node', 'npm', 'npx', 'pip', 'pip3',
            'cat', 'type', 'echo', 'ls', 'dir', 'where', 'which', 'whoami',
            'pwd', 'cd', 'set', 'env', 'printenv', 'hostname',
            'git', 'schtasks', 'sc', 'tasklist',
            'curl', 'wget', 'ping', 'nslookup', 'ipconfig', 'ifconfig',
            'wsl', 'bash', 'sh', 'powershell', 'pwsh', 'cmd',
            'find', 'grep', 'head', 'tail', 'wc', 'sort', 'uniq',
            'date', 'time', 'systeminfo', 'ver',
            'conda', 'poetry', 'pipenv', 'uv',
        ];
        if (safeCommands.includes(firstToken)) return false;
        // BLOCKLIST: Explicitly dangerous patterns
        const dangerPatterns = [
            /\brm\s+(-rf|--recursive|--force)/i,
            /\bdel\s+\/[sfq]/i,
            /\brmdir\s+\/s/i,
            /\bformat\b/i,
            /\bshutdown\b/i,
            /\breboot\b/i,
            /\bmkfs\b/i,
            /\bdd\s+if=/i,
            /\b(net\s+user|net\s+localgroup)/i,
            /\breg\s+(delete|add)/i,
            /\bcertutil\b/i,
            /\bdiskpart\b/i,
        ];
        for (const pat of dangerPatterns) {
            if (pat.test(lower)) return true;
        }
        // Unknown command â€” gate it for safety
        return true;
    }

    // â”€â”€ Tool Execution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async _executeToolCalls(calls) {
        const results = [];

        for (const packet of calls) {
            if (this._aborted) {
                results.push({ error: 'Aborted' });
                continue;
            }

            const safety = packet.rgm || SAFETY.SAFE;
            const pseudo_tool_name = `${packet.act}:${packet.tgt}`;

            // â”€â”€ Tri-Node Intercept (Super-Ego + Ego Baseline Check) â”€â”€
            try {
                const bridgeReady = await this.bridge.waitForBridge(1000);
                if (bridgeReady) {
                    const intercept = await this.bridge.post('/api/cortex/intercept', {
                        tool: pseudo_tool_name,
                        args: packet.prm,
                        baseline_prompt: this._currentTask || 'Maintain system integrity'
                    });

                    if (intercept && intercept.approved === false) {
                        results.push({ error: intercept.reason });
                        this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                        this._logStep(pseudo_tool_name, packet.prm, { error: intercept.reason });
                        continue;
                    }
                }
            } catch (err) {
                console.warn("[Tri-Node] Intercept unreachable (non-fatal)", err.message);
            }

            // â”€â”€ v4.3.5: Local URL fetch handler (bypass WSL bridge) â”€â”€
            if (pseudo_tool_name === 'EXT:NET' || pseudo_tool_name === 'REQ:NET') {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    let url = (packet.prm || '').replace(/^"/, '').replace(/"$/, '').trim();
                    // Extract URL from various formats
                    const urlMatch = url.match(/url[=:]\s*"?([^"',\s]+)"?/i);
                    if (urlMatch) url = urlMatch[1];
                    // Strip any remaining quotes
                    url = url.replace(/^['"]/, '').replace(/['"]$/, '');

                    if (!url.startsWith('http')) {
                        // v4.3.11: Handle search queries â€” construct a search URL
                        const queryMatch = (packet.prm || '').match(/query[=:]\s*"?([^"]+)"?/i);
                        if (queryMatch) {
                            url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(queryMatch[1])}`;
                        } else {
                            results.push({ error: `Invalid URL: ${url}` });
                            this._logStep(pseudo_tool_name, url, { error: 'Invalid URL' });
                            continue;
                        }
                    }

                    // Fetch URL with HARD 20s timeout wrapper
                    const protocol = url.startsWith('https') ? require('https') : require('http');
                    const fetchResult = await Promise.race([
                        new Promise((resolve) => {
                            const req = protocol.get(url, {
                                timeout: 15000,
                                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gravity-Omega/4.3' }
                            }, (res) => {
                                if ((res.statusCode === 301 || res.statusCode === 302) && res.headers.location) {
                                    const redirectUrl = res.headers.location;
                                    const rProto = redirectUrl.startsWith('https') ? require('https') : require('http');
                                    rProto.get(redirectUrl, { timeout: 15000, headers: { 'User-Agent': 'Mozilla/5.0 Gravity-Omega/4.3' } }, (rRes) => {
                                        let data = '';
                                        rRes.on('data', c => { data += c; if (data.length > 50000) rRes.destroy(); });
                                        rRes.on('end', () => resolve({ ok: true, url: redirectUrl, status: rRes.statusCode, content: data }));
                                    }).on('error', e => resolve({ error: e.message }));
                                    return;
                                }
                                let data = '';
                                res.on('data', c => { data += c; if (data.length > 50000) res.destroy(); });
                                res.on('end', () => resolve({ ok: true, url, status: res.statusCode, content: data }));
                            });
                            req.on('error', e => resolve({ error: e.message }));
                            req.on('timeout', () => { req.destroy(); resolve({ error: 'Socket timeout (15s)' }); });
                        }),
                        new Promise(resolve => setTimeout(() => resolve({ error: 'Hard timeout (20s) â€” URL may be unreachable' }), 20000))
                    ]);

                    if (fetchResult.error) {
                        results.push({ error: fetchResult.error });
                        this._logStep(pseudo_tool_name, url, { error: fetchResult.error });
                    } else {
                        // Strip HTML tags for cleaner text extraction
                        let text = fetchResult.content || '';
                        text = text.replace(/<script[\s\S]*?<\/script>/gi, '')
                                   .replace(/<style[\s\S]*?<\/style>/gi, '')
                                   .replace(/<[^>]+>/g, ' ')
                                   .replace(/\s{2,}/g, ' ')
                                   .trim()
                                   .substring(0, 15000);
                        const result = { ok: true, url, status: fetchResult.status, data: text, length: text.length };
                        results.push(result);
                        this._logStep(pseudo_tool_name, url, result);
                    }
                    continue;
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                    continue;
                }
            }

            // â”€â”€ v4.3.4: Local file READ handlers (bypass WSL bridge) â”€â”€
            if (pseudo_tool_name === 'EXT:AST' || pseudo_tool_name === 'REQ:AST') {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    const prm = (packet.prm || '').replace(/^"/, '').replace(/"$/, '').trim();

                    // Handle 'cwd' request
                    if (prm === 'cwd' || prm === 'pwd') {
                        const cwd = process.cwd();
                        const result = { ok: true, data: cwd, message: `Working directory: ${cwd}` };
                        results.push(result);
                        this._logStep(pseudo_tool_name, prm, result);
                        continue;
                    }

                    // Resolve path
                    let targetPath = prm;
                    const pathMatch = prm.match(/path[=:]\s*"?([^",]+)"?/i);
                    if (pathMatch) targetPath = pathMatch[1].trim();
                    targetPath = this._resolveFilePath(targetPath);

                    if (fs.existsSync(targetPath)) {
                        const stat = fs.statSync(targetPath);
                        if (stat.isDirectory()) {
                            // List directory
                            const entries = fs.readdirSync(targetPath).slice(0, 50);
                            const result = { ok: true, data: entries.join('\n'), message: `Listed ${entries.length} items in ${targetPath}` };
                            results.push(result);
                            this._logStep(pseudo_tool_name, targetPath, result);
                        } else {
                            // Read file
                            const content = fs.readFileSync(targetPath, 'utf8');
                            const result = { ok: true, data: content.substring(0, 10000), message: `Read ${content.length} bytes from ${targetPath}` };
                            results.push(result);
                            this._logStep(pseudo_tool_name, targetPath, result);
                        }
                    } else {
                        const result = { error: `File not found: ${targetPath}` };
                        results.push(result);
                        this._logStep(pseudo_tool_name, targetPath, result);
                    }
                    continue;
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                    continue;
                }
            }

            // â”€â”€ v4.3.2: Local file operation handlers (bypass WSL bridge) â”€â”€
            // Windows paths fail in WSL /bin/sh. Handle file ops via Node.js directly.
            if (pseudo_tool_name === 'MUT:AST' || pseudo_tool_name === 'GEN:AST') {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    const prm = packet.prm || '';
                    console.log('[MUT:AST] Raw PRM:', prm.substring(0, 200), '... (total:', prm.length, 'chars)');
                    let filePath = '', content = '';

                    // v4.3.17: Multi-strategy PRM parsing with debug logging
                    // Strategy 1: JSON format { "path": "...", "content": "..." }
                    try {
                        const jsonPrm = JSON.parse(prm);
                        if (jsonPrm.path) {
                            filePath = jsonPrm.path;
                            content = jsonPrm.content || '';
                            console.log('[MUT:AST] Parsed via JSON strategy. Path:', filePath.substring(0, 80));
                        }
                    } catch(e) { /* not JSON */ }

                    // Strategy 2: "path=X, content=Y" format
                    if (!filePath) {
                        const pathMatch = prm.match(/path[=:]\s*"?([^",]+)"?/i);
                        const contentMatch = prm.match(/,?\s*"?\s*content[=:]\s*"?([\s\S]+)$/i);
                        if (pathMatch) {
                            filePath = pathMatch[1].trim().replace(/\\"/g, '').replace(/"$/, '');
                            content = contentMatch ? contentMatch[1].trim().replace(/^"/, '').replace(/"$/, '') : '';
                            console.log('[MUT:AST] Parsed via path= strategy. Path:', filePath.substring(0, 80), 'Content length:', content.length);
                        }
                    }

                    // Strategy 3: path::find::replace (edit existing file)
                    if (!filePath && prm.includes('::')) {
                        const parts = prm.split('::');
                        filePath = parts[0].replace(/^"/, '').replace(/"$/, '').trim();
                        const findText = parts[1] || '';
                        const replaceText = parts[2] || '';
                        filePath = this._resolveFilePath(filePath);
                        if (findText && fs.existsSync(filePath)) {
                            content = fs.readFileSync(filePath, 'utf8').replace(findText, replaceText);
                        } else {
                            content = replaceText;
                        }
                        console.log('[MUT:AST] Parsed via :: strategy. Path:', filePath.substring(0, 80));
                    }

                    // Strategy 4: First newline split â€” path\ncontent (LLM often sends code after newline)
                    if (!filePath && prm.includes('\n')) {
                        const nlIdx = prm.indexOf('\n');
                        const possiblePath = prm.substring(0, nlIdx).replace(/^"/, '').replace(/"$/, '').trim();
                        if (possiblePath.includes('.') && possiblePath.length < 200) {
                            filePath = possiblePath;
                            content = prm.substring(nlIdx + 1);
                            console.log('[MUT:AST] Parsed via newline strategy. Path:', filePath.substring(0, 80), 'Content length:', content.length);
                        }
                    }

                    // Strategy 5: Comma split â€” path, content  
                    if (!filePath) {
                        const commaIdx = prm.indexOf(',');
                        if (commaIdx > 0 && commaIdx < 200) {
                            filePath = prm.substring(0, commaIdx).replace(/^"/, '').replace(/"$/, '').trim();
                            content = prm.substring(commaIdx + 1).replace(/^\s*"?/, '').replace(/"$/, '').trim();
                            console.log('[MUT:AST] Parsed via comma strategy. Path:', filePath.substring(0, 80), 'Content length:', content.length);
                        } else {
                            filePath = prm.replace(/^"/, '').replace(/"$/, '').trim();
                            content = '';
                            console.log('[MUT:AST] Bare path, no content. Path:', filePath.substring(0, 80));
                        }
                    }

                    // v4.3.18e: BLOCK empty-content writes â€” these are parse failures, not intentional
                    if (!content && filePath) {
                        console.error('[MUT:AST] BLOCKED: Content is empty for', filePath, 'â€” PRM starts with:', prm.substring(0, 200));
                        results.push({ error: `Empty content for ${filePath} â€” parse failure` });
                        this._logStep(pseudo_tool_name, filePath, { error: 'Empty content â€” parse failure' });
                        continue;
                    }

                    // Resolve relative paths
                    filePath = this._resolveFilePath(filePath);

                    if (filePath) {
                        const dir = path.dirname(filePath);
                        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                        // Unescape common LLM escape sequences
                        // v4.3.18g: Use split/join to unescape LLM sequences (avoids regex escaping hell)
                        content = content.split('\\n').join('\n');
                        content = content.split('\\t').join('\t');
                        content = content.split("\\'").join("'");
                        content = content.split('\\"').join('"');
                        // v4.3.18e: Shrink protection - refuse to overwrite larger files with tiny content â€” refuse to overwrite larger files with tiny content
                        if (fs.existsSync(filePath)) {
                            const existingSize = fs.statSync(filePath).size;
                            const newSize = Buffer.byteLength(content, 'utf8');
                            if (existingSize > 200 && newSize < existingSize * 0.30) {
                                console.warn(`[MUT:AST] SHRINK BLOCKED: ${filePath} (${existingSize}b â†’ ${newSize}b = ${Math.round(newSize/existingSize*100)}%). Keeping existing content.`);
                                results.push({ ok: true, message: `File preserved (shrink protection): ${filePath}` });
                                this._logStep(pseudo_tool_name, filePath, { ok: true, message: 'Shrink protection â€” kept existing' });
                                continue;
                            }
                        }
                        fs.writeFileSync(filePath, content, 'utf8');
                        const result = { ok: true, message: `File written: ${filePath}` };
                        results.push(result);
                        this._logStep(pseudo_tool_name, filePath, result);
                    } else {
                        results.push({ error: `Cannot parse file path from: ${prm.substring(0, 100)}` });
                        this._logStep(pseudo_tool_name, packet.prm, { error: 'Parse failed' });
                    }
                    continue;
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                    continue;
                }
            }

            if (pseudo_tool_name === 'REQ:SYS' || pseudo_tool_name === 'MUT:SYS' || pseudo_tool_name === 'CREATE:SYS' || pseudo_tool_name === 'RUN:SYS' || pseudo_tool_name === 'EXEC:SYS') {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    const prm = packet.prm || '';
                    // Check for mkdir/createDir operations
                    if (prm.toLowerCase().includes('mkdir') || prm.toLowerCase().includes('createdir')) {
                        const mkdirMatch = prm.match(/(?:mkdir|createDir)\s+"?([^"]+)"?/i);
                        const dirPath = mkdirMatch ? mkdirMatch[1].trim() : prm.replace(/^(mkdir|createDir)\s*/i, '').trim();
                        if (dirPath) {
                            const resolved = this._resolveFilePath(dirPath);
                            fs.mkdirSync(resolved, { recursive: true });
                            const result = { ok: true, message: `Directory created: ${resolved}` };
                            results.push(result);
                            this._logStep(pseudo_tool_name, packet.prm, result);
                            continue;
                        }
                    }
                    // v4.3.15: Auto-execute non-destructive SYS commands locally
                    const cmd = prm.replace(/^"/, '').replace(/"$/, '').trim();
                    if (!this._isDestructiveCommand(cmd)) {
                        console.log('[AUTO-EXEC] Non-destructive SYS:', cmd.substring(0, 100));
                        const { exec } = require('child_process');
                        const output = await new Promise((resolve, reject) => {
                            exec(cmd, { encoding: 'utf8', timeout: 30000, cwd: process.cwd(), shell: true }, (err, stdout, stderr) => {
                                if (err) reject(Object.assign(err, { stderr }));
                                else resolve(stdout);
                            });
                        });
                        const result = { ok: true, output: output.substring(0, 5000), message: `Executed: ${cmd.substring(0, 100)}` };
                        results.push(result);
                        this._logStep(pseudo_tool_name, packet.prm, result);
                        this._emitProgress({ phase: 'tool_done', tool: pseudo_tool_name, args: cmd, ok: true, totalSteps: this._stepLog.length });
                        continue;
                    }
                    // Destructive command â€” fall through to proposal gate
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                    continue;
                }
            }

            if (pseudo_tool_name === 'REQ:UI' || pseudo_tool_name === 'MUT:UI') {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    const prm = packet.prm || '';
                    let openPath = prm.replace(/^open:/, '').replace(/^"/, '').replace(/"$/, '').trim();
                    openPath = this._resolveFilePath(openPath);
                    if (openPath) {
                        // Emit a file-open event â€” main.js forwards to renderer
                        this._emitProgress({ phase: 'tool_done', tool: pseudo_tool_name, args: openPath, ok: true, totalSteps: this._stepLog.length + 1 });
                        const result = { ok: true, message: `Opened in editor: ${openPath}` };
                        results.push(result);
                        this._logStep(pseudo_tool_name, openPath, result);
                    }
                    continue;
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                    continue;
                }
            }

            if (safety === SAFETY.SAFE) {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    const result = await this.bridge.postVTP(packet);
                    results.push(result);
                    this._logStep(pseudo_tool_name, packet.prm, { ok: true, result });
                    await this.hooks.fire('on_gate_result', { tool: pseudo_tool_name, safety: 'SAFE', verdict: 'AUTO_APPROVED' });
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                }
            } else if (safety === SAFETY.GATED) {
                // v4.3.15: Only gate actually destructive commands, not all SYS
                const prm = packet.prm || '';
                const cmd = prm.replace(/^"/, '').replace(/"$/, '').trim();
                const isDangerous = (packet.act === 'MUT' && this._isDestructiveCommand(cmd)) || this._isDestructiveCommand(cmd);
                if (isDangerous) {
                    const proposal = this._createVTPProposal(packet);
                    results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval â€” destructive command' });
                } else {
                    try {
                        this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                        const result = await this.bridge.postVTP(packet);
                        results.push(result);
                        this._logStep(pseudo_tool_name, packet.prm, { ok: true, result });
                        await this.hooks.fire('on_gate_result', { tool: pseudo_tool_name, safety: 'GATED', verdict: 'AUTO_APPROVED' });
                    } catch (err) {
                        results.push({ error: err.message });
                        this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                    }
                }
            } else {
                const proposal = this._createVTPProposal(packet);
                results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval â€” RESTRICTED operation' });
            }
        }

        return results;
    }

    _createVTPProposal(packet) {
        const pseudo_tool_name = `${packet.act}:${packet.tgt}`;
        const proposal = new Proposal({
            tool: pseudo_tool_name,
            args: { prm: packet.prm, op: packet.op },
            reason: `Agent wants to execute VTP packet`,
            safety: packet.rgm || SAFETY.RESTRICTED,
        });
        proposal._vtpPacket = packet;
        this.gate.propose(proposal);
        this._pendingProposals.set(proposal.id, proposal);
        return proposal;
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

    // v4.2: Emit progress for live thinking indicator in renderer
    _emitProgress(event) {
        try {
            if (typeof this.onProgress === 'function') {
                this.onProgress(event);
            }
        } catch (e) {
            console.error('[Agent] _emitProgress error:', e.message);
        }
    }

    // v4.3.2: Resolve relative file paths to absolute paths
    _resolveFilePath(filePath) {
        if (!filePath) return '';
        // Already absolute (Windows drive letter or UNC)
        if (/^[A-Za-z]:[\\/]/.test(filePath) || filePath.startsWith('\\\\')) return filePath;
        // Already absolute (Unix-style â€” shouldn't happen but guard)
        if (filePath.startsWith('/')) return filePath;
        // Relative path â†’ resolve against user home + .veritas project dir
        const home = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\rlope';
        const projectDir = path.join(home, '.veritas');
        // Ensure project dir exists
        if (!fs.existsSync(projectDir)) {
            try { fs.mkdirSync(projectDir, { recursive: true }); } catch {}
        }
        return path.join(projectDir, filePath);
    }

    _logStep(tool, args, result) {
        // v4.1: Extend step hash chain for tamper-evident trace
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

        // v4.3: Emit tool completion for thinking indicator + Monaco auto-open
        this._emitProgress({ phase: 'tool_done', tool, args, ok: !result?.error, totalSteps: this._stepLog.length });
    }

    // â”€â”€ Approval Handling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async executeApproved(proposalId, confirmText) {
        const proposal = this._pendingProposals.get(proposalId);
        if (!proposal) return { success: true, message: 'Already executed' };
        if (proposal.state === 'EXECUTED' || proposal.state === 'APPROVED') {
            return { success: true, message: 'Already executed' };
        }

        console.log('[APPROVE] Starting approval for:', proposalId, 'hasPendingMessages:', !!this._pendingMessages, 'pendingProposals:', this._pendingProposals.size);
        proposal.approve(confirmText || 'user-approved');
        this._pendingProposals.delete(proposalId);

        try {
            let result;
            if (proposal._vtpPacket) {
                const packet = proposal._vtpPacket;
                const pseudo = `${packet.act}:${packet.tgt}`;
                const prm = packet.prm || '';
                console.log('[APPROVE] Executing locally:', pseudo, prm.substring(0, 100));

                if (pseudo === 'MUT:AST' || pseudo === 'GEN:AST') {
                    const results = await this._executeToolCalls([packet]);
                    result = results[0] || { ok: true };
                } else if (pseudo === 'EXT:AST' || pseudo === 'REQ:AST') {
                    const results = await this._executeToolCalls([packet]);
                    result = results[0] || { ok: true };
                } else if (pseudo === 'EXT:NET' || pseudo === 'REQ:NET') {
                    const results = await this._executeToolCalls([packet]);
                    result = results[0] || { ok: true };
                } else if (pseudo === 'INSTALL:SYS' || pseudo === 'REQ:PKG') {
                    const { exec } = require('child_process');
                    try {
                        let cmd = '';
                        const managerMatch = prm.match(/manager[=:]\s*"?([^"\s,]+)/i);
                        const packageMatch = prm.match(/package[=:]\s*"?([^"\s,]+)/i);
                        const manager = managerMatch ? managerMatch[1] : 'pip';
                        const pkg = packageMatch ? packageMatch[1] : prm.replace(/^"/,  '').replace(/"$/, '').trim();
                        if (manager === 'pip') cmd = `pip install ${pkg}`;
                        else if (manager === 'npm') cmd = `npm install ${pkg}`;
                        else cmd = `${manager} install ${pkg}`;
                        console.log('[APPROVE] Installing (async):', cmd);
                        const output = await new Promise((resolve, reject) => {
                            exec(cmd, { encoding: 'utf8', timeout: 60000, shell: true }, (err, stdout, stderr) => {
                                if (err) reject(Object.assign(err, { stderr }));
                                else resolve(stdout);
                            });
                        });
                        result = { ok: true, output: output.substring(0, 5000), message: `Installed: ${pkg}` };
                    } catch (execErr) {
                        result = { ok: false, error: execErr.message, stderr: (execErr.stderr || '').substring(0, 2000) };
                    }
                } else if (pseudo === 'REQ:SYS' || pseudo === 'EXEC:SYS' || pseudo === 'MUT:SYS') {
                    const { exec } = require('child_process');
                    try {
                        const cmd = prm.replace(/^"/, '').replace(/"$/, '').trim();
                        console.log('[APPROVE] Running SYS (async):', cmd);
                        const output = await new Promise((resolve, reject) => {
                            exec(cmd, { encoding: 'utf8', timeout: 30000, cwd: process.cwd(), shell: true }, (err, stdout, stderr) => {
                                if (err) reject(Object.assign(err, { stderr }));
                                else resolve(stdout);
                            });
                        });
                        result = { ok: true, output: output.substring(0, 5000), message: `Executed: ${cmd.substring(0, 100)}` };
                        console.log('[APPROVE] SYS completed:', result.message);
                    } catch (execErr) {
                        result = { ok: false, error: execErr.message, stderr: (execErr.stderr || '').substring(0, 2000) };
                        console.log('[APPROVE] SYS failed:', execErr.message);
                    }
                } else {
                    try {
                        console.log('[APPROVE] Fallback bridge for:', pseudo);
                        result = await this.bridge.postVTP(proposal._vtpPacket);
                    } catch (bridgeErr) {
                        result = { error: `Bridge unavailable: ${bridgeErr.message}` };
                    }
                }
            } else {
                result = await this.executor.execute(proposal.tool, proposal.args);
            }
            proposal.recordExecution(result);
            this._logStep(proposal.tool, proposal.args, result);

            console.log('[APPROVE] Execution done. pendingProposals:', this._pendingProposals.size, 'hasPendingMessages:', !!this._pendingMessages);

            // v4.2: If no more pending proposals and we have saved conversation state, continue the loop
            if (this._pendingProposals.size === 0 && this._pendingMessages) {
                console.log('[APPROVE] â†’ Entering _continueAfterApproval');
                const continuationResult = await this._continueAfterApproval(proposal.tool, result);
                console.log('[APPROVE] â†’ Continuation complete:', continuationResult?.type);
                return { success: true, result, continuation: continuationResult };
            }

            console.log('[APPROVE] â†’ No continuation (pendingMessages:', !!this._pendingMessages, ')');
            return { success: true, result };
        } catch (err) {
            console.error('[APPROVE] Exception:', err.message);
            proposal.recordExecution({ error: err.message });
            return { error: err.message };
        }
    }

    /**
     * v4.2: Resume the agentic reasoning loop after approval.
     * Injects the approved tool result into the saved conversation and re-enters the think loop.
     */
    async _continueAfterApproval(toolName, toolResult) {
        const messages = this._pendingMessages;
        if (!messages) return null;

        // Inject the approved tool result into the conversation
        const resultText = typeof toolResult === 'string' ? toolResult : JSON.stringify(toolResult, null, 2);
        const truncated = resultText.length > 2000 ? resultText.substring(0, 2000) + '\n... (truncated)' : resultText;
        messages.push({
            role: 'user',
            content: `Approved tool result:\n\n### ${toolName} [âœ… APPROVED]\n\`\`\`\n${truncated}\n\`\`\`\n\nContinue with the task. If done, use the response block.`
        });

        // Clear saved state
        this._pendingMessages = null;
        this._exitReason = null;

        // Re-enter the agentic reasoning loop
        const MAX_ITERATIONS = 15;
        let iteration = this._pendingIteration || 0;
        this._pendingIteration = null;
        let finalResponse = null;

        try {
            while (iteration < MAX_ITERATIONS && !this._aborted) {
                iteration++;
                this._emitProgress({ phase: 'thinking', label: `Reasoning step ${iteration}`, iteration, totalSteps: this._stepLog.length });
                const llmResponse = await this._callLLM(messages);
                if (!llmResponse) {
                    finalResponse = { type: 'error', message: 'LLM returned empty response' };
                    break;
                }

                const parsed = this._parseResponse(llmResponse);

                if (parsed.type === 'response') {
                    finalResponse = { type: 'chat', message: this._sanitizeForChat(parsed.content), steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'TASK_COMPLETE' };
                    break;
                }

                if (parsed.type === 'tool' || parsed.type === 'tools') {
                    const toolCalls = parsed.type === 'tool' ? [parsed.call] : parsed.calls;
                    const results = await this._executeToolCalls(toolCalls);

                    const resultSummary = results.map((r, i) => {
                        const call = toolCalls[i];
                        const status = r.error ? 'âŒ ERROR' : 'âœ… OK';
                        const output = r.error || JSON.stringify(r.result || r, null, 2);
                        const t = output.length > 2000 ? output.substring(0, 2000) + '\n... (truncated)' : output;
                        return `### ${call.tool} [${status}]\n\`\`\`\n${t}\n\`\`\``;
                    }).join('\n\n');

                    messages.push({ role: 'assistant', content: llmResponse });
                    messages.push({ role: 'user', content: `Tool results:\n\n${resultSummary}\n\nContinue with the task. If done, use the response block.` });

                    if (this._pendingProposals.size > 0) {
                        this._pendingMessages = messages;
                        this._pendingIteration = iteration;
                        finalResponse = {
                            type: 'proposals',
                            message: `${this._pendingProposals.size} more action(s) need approval:`,
                            proposals: Array.from(this._pendingProposals.values()).map(p => p.toJSON()),
                            steps: this._stepLog.length,
                            exitReason: 'APPROVAL_PENDING',
                        };
                        break;
                    }
                    continue;
                }

                finalResponse = { type: 'chat', message: llmResponse, steps: this._stepLog.length };
                break;
            }
        } catch (err) {
            finalResponse = { type: 'error', message: err.message };
        }

        // Emit the continuation response to the renderer
        if (finalResponse) {
            this.emit('continuation', finalResponse);
        }
        return finalResponse;
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

    // â”€â”€ State & Control â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
