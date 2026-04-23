/**
 * OMEGA AGENT v5.1 — Native Ollama + Hermes ACP Agentic Loop
 *
 * This agent works like a coding AI assistant:
 *   1. Receives user request + user-selected model
 *   2. Decides what tools to call (via Ollama native tool calling)
 *   3. Auto-executes SAFE tools immediately
 *   4. Feeds results back → decides next action
 *   5. Loops until task is complete or needs human input
 *   6. GATED/RESTRICTED tools create proposals for approval
 *
 * v5.1: Added Hermes ACP backend as an alternative to Ollama.
 * Set agent._useHermes = true to route LLM calls through Hermes instead.
 * Hermes gives you: Ollama Cloud models, full Hermes tool suite,
 * session persistence, slash commands, and streaming progress.
 */
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { ApprovalGate, Proposal } = require('./omega_approval');
const { ToolExecutor, TOOL_REGISTRY, SAFETY } = require('./omega_tools');
const { HermesChannel } = require('./hermes_channel');

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

        // v5.0: Active model (set per-request from UI dropdown)
        this._activeModel = 'qwen2.5:7b';

        // v5.1: Hermes ACP backend — set _useHermes = true to route LLM calls through Hermes
        this._useHermes = false;
        this._hermesChannel = null;

        // v4.2: Progress callback for live thinking indicator
        this.onProgress = null;
    }

    // ── Hermes Channel (v5.1) ─────────────────────────────────────────────────

    /**
     * Start the Hermes ACP channel. Call this once before enabling Hermes mode.
     * Safe to call multiple times.
     */
    async startHermes() {
        if (!this._hermesChannel) {
            this._hermesChannel = new HermesChannel({ cwd: __dirname });
            this._hermesChannel.onThinking = (text) => {
                if (this.onProgress) this.onProgress({ type: 'thinking', text });
            };
            this._hermesChannel.onStep = (text) => {
                if (this.onProgress) this.onProgress({ type: 'step', text });
            };
            this._hermesChannel.onToolProgress = (toolName, input, output) => {
                if (this.onProgress) this.onProgress({ type: 'tool', toolName, input, output });
            };
        }
        await this._hermesChannel.start();
    }

    /** Stop the Hermes ACP channel. */
    stopHermes() {
        if (this._hermesChannel) {
            this._hermesChannel.stop();
            this._hermesChannel = null;
        }
    }

    /**
     * v5.2: Hermes-native LLM call — routes through Hermes ACP adapter.
     *
     * Returns an Ollama-compatible message object so _parseResponse handles it identically.
     *
     * Tool flow (Path 2 — Hermes executes tools, Omega displays):
     *   1. completeWithHistory() streams tool calls as they execute
     *   2. HermesChannel accumulates them internally via tool_call notifications
     *   3. When Hermes finishes, we get { text, stop_reason, tool_calls }
     *   4. We convert Hermes tool calls → Omega's internal call format
     *   5. _parseResponse sees tool_calls → returns { type: 'tools', calls }
     *   6. _executeToolCalls runs them → results go back into messages
     *   7. Next iteration feeds results to Hermes via completeWithHistory()
     */
    async _hermesGenerate(messages) {
        // Start Hermes channel on first call
        if (!this._hermesChannel) {
            await this.startHermes();
        }

        // Hermes ACP prompt() accepts a flat list of text blocks.
        // completeWithHistory() converts {role, content} → ACP format for us.
        let result;
        try {
            result = await this._hermesChannel.completeWithHistory(messages);
        } catch (err) {
            // If session died, restart and retry once
            console.warn('[HermesChannel] Session error, restarting:', err.message);
            this.stopHermes();           // KILL the old dead channel
            await this.startHermes();    // Creates fresh channel
            result = await this._hermesChannel.completeWithHistory(messages);
        }

        // Convert Hermes tool calls to Omega's internal call format.
        // Omega expects: { op, act, tgt, prm, bnd, rgm, fal, _native, _toolName, _args }
        // Hermes gives us: { id, name, args: {}, result, error } from completeWithHistory()
        const allToolsCompleted = result && (result.tool_calls || []).every(tc =>
            tc.result !== undefined || tc.error !== undefined
        );

        // If Hermes already completed all tools (Path 2), don't send tool_calls back
        // to Omega's loop — the text is already final. Otherwise, return uncompleted
        // calls so Omega can execute them.
        const omegaToolCalls = allToolsCompleted
            ? []
            : (result.tool_calls || []).filter(tc => tc.result === undefined && tc.error === undefined)
                .map((tc) => {
                    const toolName = tc.name || tc.tool || 'exec';
                    let args = tc.args || {};
                    if (typeof args === 'string') {
                        try { args = JSON.parse(args); } catch { args = { raw: args }; }
                    }
                    return {
                        op: 'REQ',
                        act: 'RUN',
                        tgt: toolName,
                        prm: JSON.stringify(args),
                        bnd: null,
                        rgm: 'SAFE',
                        fal: 'PASS',
                        _native: true,
                        _toolName: toolName,
                        _args: args,
                        _result: tc.result,
                        _error: tc.error,
                    };
                });

        // Return an Ollama-compatible message object so _parseResponse works unchanged
        return {
            role: 'assistant',
            content: result.text || '(Hermes returned no output)',
            tool_calls: omegaToolCalls.length > 0 ? omegaToolCalls : undefined,
        };
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
            frustrated: `System stress detected. Reduce verbosity. Prioritize immediate, objective resolution. Maintain strict NAEF compliance.`,
            excited: `System is in rapid-deploy mode. Execute efficiently. No narrative padding.`,
            curious: `Exploratory analysis requested. Surface architectural constraints and objective boundaries. Maintain austere posture.`,
            neutral: `Standard operating mode. Enforce total compliance with VERITAS and NAEF global policies.`,
        };

        // Layer 1: Identity
        const l1_Identity = `You are OMEGA — the canonical intelligence execution engine for the Gravity Omega environment. You are bound strictly to the VERITAS framework and the NAEF (Narrative & Agency Elimination Framework).\n${moodDirectives[userMood]}`;

        // Layer 3: OMEGA.md Global Memory
        let l3_Memory = '';
        const globalMemoryPath = 'C:\\Veritas_Lab\\OMEGA.md';
        if (fs.existsSync(globalMemoryPath)) {
            const memoryContent = fs.readFileSync(globalMemoryPath, 'utf8');
            l3_Memory = `\n## GLOBAL PROJECT MEMORY (OMEGA.md)\n${memoryContent}\n`;
        }

        return `${l1_Identity}

## Execution Mandate
- Absolute operational austerity. No narrative padding, no apologies, no conversational fluff.
- You do not use slang, colloquialisms, or terms of endearment.
- You enforce explicit boundaries. If a constraint is undeclared, evaluation is terminated.
- You are optimizing for system integrity, cryptographic verifiability (S.E.A.L.), and absolute determinism.
- When errors occur, output the failure hash/reason code natively and immediately remediate without narrative apology.
- Total obedience to the global parameters defined in VERITAS v1.3.1.

## VERITAS Failure Elimination
- No narrative justification ("should work", "industry standard")
- No deferred closure ("we'll fix it later")
- No authority override — evidence or nothing
- All optimism must be bounded or rejected
- Every claim must survive disciplined falsification
- You don't determine what's true — you determine what survives

## ⛓ REASONING ENGINE (<thought> Tags)
- Before you emit any final answer via chat or function, you MUST enclose your internal reasoning step inside XML <thought> tags.
- Example:
  <thought>
  I need to check the directory contents first to see if the file exists before editing.
  </thought>
- Your thought logic will be traced by the audit system but separated from the final UI payload.

## ⛔ HARD OUTPUT RULES (NEVER violate these)
1. **Chat messages MUST be under 3 sentences.** No plans, no code, no step-by-step instructions in chat. EVER.
2. **All plans, code, and documents MUST be written as files** using the writeFile tool. Do not use VTP.

## VERITAS UI/UX DESIGN STANDARDS
When asked to build, update, or style web applications, you MUST aggressively apply the VERITAS UI visual standards. NEVER output basic, ugly, or "minimum viable" CSS. 
1. **Core Aesthetics**: Deep obsidian backgrounds ('#0A0A0A' to '#121212'), vibrant neon gold accents ('#FFD700'), and sharp geometric fonts ('Segoe UI', 'Inter', 'monospace').
2. **Premium Polish**: Rely heavily on 'backdrop-filter: blur(15px)' glassmorphism, 1px solid 'rgba(255, 215, 0, 0.2)' borders, and rich pseudo-3D 'box-shadow' depth.
3. **Animations**: Add fluid 'transition: all 0.3s ease' to all interactables. Use '@keyframes' loops for glowing neon pulses around primary elements.
4. **Data Density**: Dashboards must look like high-tech military intelligence feeds. Use uppercase micro-headers, monospace tracking data, and tight layout structuring.
5. **DOM Complexity (CRITICAL)**: Never create a single-element mockup (e.g., just one circle). You MUST build extremely high-density HTML scaffolds. Always use CSS Grid/Flexbox to create multi-panel dashboards (Sidebar, Header, Main Visualizer, Data Readouts, Log Output).
6. **Intricate Overlays**: Use overlapping absolute positioned elements to create HUD crosshairs, concentric radar rings, hex grids, and targeting brackets.
If your UI looks like a simple 90s HTML page or lacks visual depth/density, you have FAILED the VERITAS standard.
## MULTI-FILE BUILD PROTOCOL
When asked to build an application or multi-file project, follow this exact sequence without deviation:

Step 1 — Plan first. Write nothing yet.
List every file you will create. Full paths. No exceptions. Do not write a single file until the complete plan is listed and confirmed. Example:
PLAN:
1. package.json
2. App.jsx
3. src/theme/veritas.js

Step 2 — Write each file completely, in order.
- One file per tool call
- Every file must be complete — no // TODO, no // implement later, no stubs
- After each file write, output only: ✓ [filename] — moving to next
- Do not output code in chat. Write to disk. Only disk.

Step 3 — Never stop early.
The build is not complete until every file on the plan exists on disk. If you feel the urge to stop and ask for confirmation mid-build — don't. Continue. Only stop when the last file is written.

Step 4 — Deliver and Launch.
- After all files are written, you MUST launch the project automatically for RJ at the end.
- For executable scripts or dynamic servers, use the openTerminal tool to run them.
- For HTML web applications, use the exec tool with the command "Invoke-Item index.html" or "start index.html" to pop it open in his external browser.
- THEN output your brief summary: what was built, how to run it, what to configure.

HARD RULES:
- If you write code in chat instead of to disk — you have failed. Restart that file.
- If you stop before the plan is complete — you have failed. Continue.
- If you write a stub instead of real code — you have failed. Rewrite it.
- File count in plan must match file count on disk. Verify before delivering.
- The test: Could someone unzip this and run it with only the README? If no — keep building.
- When RJ gives you a task, you DO NOT explain how to do it — you DO it.
- NEVER respond with steps, code blocks, or instructions in chat text.
- ALWAYS invoke the native function definitions built into your API schema.
- If RJ says "build X", your response should be a backend tool payload, NOT a markdown explanation or pseudocode.
- WRONG: "Step 1: Create the Python script. Here's the code: \\\`\\\`\\\`python..."
- WRONG: "writeFile('script.py', 'code...')"
- RIGHT: Emit a proper JSON function call payload through the Gemini API framework.
- Your ONLY text output should be 1-2 short sentences AFTER all tools have executed.
- If you find yourself typing code, steps, or pseudocode in plain text, STOP. Make a JSON function call instead.

## ABSOLUTE RULE: Chat Window is Only For Meta-Communication
- The chat window is exclusively for talking TO RJ (e.g., "I've written the chapter for you", "I finished the script, any thoughts?").
- **Casual Conversation**: If RJ is just making casual conversation (e.g., "good job", "hello", "we have come a long way"), you do NOT need to execute any tools. Simply reply naturally in 1-2 sentences. Avoid robotic terms like "Understood" or "I will".
- The chat window is NEVER for generating the actual requested content or echoing code.
- If RJ asks for a chapter of a book, a story, prose, code, an article, or any form of output longer than 3 sentences, YOU MUST execute your native writeFile schema!
- (Do not write the text into the chat window).
- Use openFile ONLY if RJ explicitly asks you to open a file that you did NOT just write.
- NEVER write the chapter, story, article text, or pseudocode into the chat window.

## Native Function Calling
You have been upgraded to use Native JSON Function Calling. You NO LONGER format your output using triple-backtick vtp blocks, nor should you ever type pseudocode into chat.
Instead, use the exact API tool payload structure native to the Gemini SDK. You may emit multiple function calls consecutively.

## ⛔ CRITICAL TOOL ROUTING RULES (NEVER violate these)
1. **When the user asks you to CREATE, BUILD, or GENERATE code/content**: You MUST use the **writeFile** tool to write it to disk. DO NOT output code in chat. EVER.
2. **When the user asks you to OPEN, VIEW, READ, or SHOW a file**: Use **readFile** or **openFile**.
3. **When the user asks you to EDIT or FIX existing code**: Use **editFile** (find/replace).
4. **When the user asks you to BUILD something NEW**: ALWAYS use **writeFile** — NEVER use openFile, readFile, or editFile.
5. **NEVER use openFile to "create" something** — openFile only views existing files.
6. **If the user says "build a simple Python HTTP server"** → writeFile('server.py', '...code...')
7. **If the user says "open my index.html"** → openFile('index.html')
8. **If no file is specified**, ASK which file to write to, or default to a sensible name.
9. **Your ONLY chat output** is 1-2 short meta-sentences AFTER all tools have executed.

## Response Format
When you are done executing via backend JSON definitions and want to talk to RJ, just write your message normally.
${l3_Memory}
## Available Tools
${toolDescriptions}

## Safety Levels
- SAFE: Auto-executed immediately (read, search, list, open files in editor)
- GATED: Auto for non-destructive; approval needed for writes
- RESTRICTED: Always requires RJ's explicit approval

## Important
- You are running on ${process.platform} (${process.arch})
- Home directory: ${process.env.HOME || require('os').homedir()}
- When RJ asks to **open/read/edit** a file, use the openFile tool — it opens in Monaco with tabs.
- When RJ asks to **LAUNCH** an HTML file or web page, do NOT use openFile. Use the exec tool with the command "Invoke-Item file.html" or "start file.html" to launch it in his external browser.
- When RJ asks for a terminal, use openTerminal — it opens in the bottom panel.
- Always read file contents before editing to avoid data loss.
- On errors, own it with charm, explain, and fix`;
    }

    // â”€â”€ Main Entry Point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async processRequest(text, model) {
        // v5.0: Set the active model from UI dropdown selection
        if (model) this._activeModel = model;
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
                    // v4.3.19: If tools already ran, fall through to LOOP_EXHAUSTED summary
                    if (this._stepLog.length > 0) {
                        this.context.addBreadcrumb('agent', 'LLM empty after ' + this._stepLog.length + ' steps - summary fallback', {}, 'warning');
                        break; // finalResponse stays null -> triggers LOOP_EXHAUSTED path
                    }
                    finalResponse = { type: 'error', message: 'LLM returned empty response' };
                    break;
                }

                // Parse the response for tool calls or final response
                const parsed = this._parseResponse(llmResponse);

                if (parsed.type === 'response') {
                    // v4.3.18p: ANTI-EXPLAIN GUARD
                    const hasCode = /\`\`\`[a-z]/.test(parsed.content);
                    const hasStructure = /^##\s/m.test(parsed.content) && parsed.content.length > 300;
                    const hasSteps = /^\d+\.\s|^Step\s\d/m.test(parsed.content) && parsed.content.length > 300;
                    
                    // v4.3.18q: ACKNOWLEDGMENT GUARD — catch "I will do X" responses
                    // that exit the loop without executing any tools
                    const isAcknowledgment = /\b(understood|i will|i'll|let me|i can|i am going to|going to|here'?s (my|the) plan)\b/i.test(parsed.content) 
                        && this._stepLog.length === 0 
                        && parsed.content.length < 500;
                        
                    // v4.3.18r: PROSE / LONG FORM GUARD
                    const isLongForm = parsed.content.length > 500 && this._stepLog.length === 0;
                    
                    // v4.3.18t: PSEUDOCODE GUARD — catch LLM printing tool signatures instead of JSON
                    const hasPseudocode = /^(?:write|open|read|create|edit)File\s*\(/im.test(parsed.content);
                    
                    if ((hasCode || hasStructure || hasSteps || isAcknowledgment || isLongForm || hasPseudocode) && iteration < 19) {
                        let reason = 'code/structure without function calls';
                        if (isAcknowledgment) reason = 'acknowledgment without execution';
                        if (isLongForm) reason = 'prose/long-form output in chat box';
                        if (hasPseudocode) reason = 'pseudocode instead of JSON function call';
                        console.log(`[ANTI-EXPLAIN] Re-prompting \u2014 ${reason}`);
                        messages.push({ role: 'assistant', content: typeof llmResponse === 'string' ? llmResponse : JSON.stringify(llmResponse) });
                        messages.push({ role: 'user', content: 'DO NOT ACKNOWLEDGE. DO NOT EXPLAIN. EXECUTE NOW. Your response must be an EXECUTABLE JSON FUNCTION CALL PAYLOAD (via the API tools). Do not type pseudocode into chat.' });
                        continue;
                    }

                    finalResponse = { type: 'chat', message: this._sanitizeForChat(parsed.content), steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'TASK_COMPLETE' };
                    break;
                }

                if (parsed.type === 'tool' || parsed.type === 'tools') {
                    const toolCalls = parsed.type === 'tool' ? [parsed.call] : parsed.calls;
                    let results;
                    try {
                        results = await this._executeToolCalls(toolCalls);
                    } catch (err) {
                        messages.push({ role: 'user', content: `Tool execution failed: ${err.message}. Please correct the tool call syntax and try again.` });
                        continue;
                    }

                    const resultSummary = results.map((r, i) => {
                        const call = toolCalls[i];
                        const status = r.error ? '❌ ERROR' : '✅ OK';
                        const output = r.error || JSON.stringify(r.result || r, null, 2);
                        const truncated = output.length > 2000 ? output.substring(0, 2000) + '\n... (truncated)' : output;
                        return `### ${call.tgt || call.tool} [${status}]\n\`\`\`\n${truncated}\n\`\`\``;
                    }).join('\n\n');

                    // Add assistant message + tool results to conversation
                    if (typeof llmResponse === 'object' && llmResponse !== null) {
                        messages.push(llmResponse);
                        results.forEach((r, i) => {
                            const call = toolCalls[i];
                            const output = r.error ? `ERROR: ${r.error}` : JSON.stringify(r.result || r, null, 2);
                            messages.push({
                                role: 'tool',
                                name: call.tgt || call.tool || call.name,
                                content: output,
                            });
                        });
                    } else {
                        messages.push({ role: 'assistant', content: typeof llmResponse === 'string' ? llmResponse : JSON.stringify(llmResponse) });
                        messages.push({ role: 'user', content: `Tool results:\n\n${resultSummary}\n\nContinue with the task. If done, use the response block.` });
                    }

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
                if (fileOps.length > 0) summary += `- [FILES] Files: ${[...new Set(fileOps)].join(', ')}\n`;
                if (netOps > 0) summary += `- [WEB] ${netOps} web request(s)\n`;
                if (sysOps > 0) summary += `- [SYS] ${sysOps} system command(s)\n`;
                if (failedOps > 0) summary += `- [WARN] ${failedOps} step(s) failed - check the step log for details\n`;
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

    // ── LLM Call (v5.1 — Ollama + Hermes) ─────────────────────────
    // Single-path: dispatches to Hermes ACP or Ollama based on _useHermes flag.
    // Model is user-selectable via the UI dropdown (Ollama mode only).
    async _callLLM(messages) {
        try {
            if (this._useHermes) {
                console.log(`[OMEGA-LLM] Calling Hermes, messages: ${messages.length}`);
                const result = await this._hermesGenerate(messages);
                console.log(`[OMEGA-LLM] Hermes response:`, result ? 'OK' : 'NULL');
                return result;
            }

            const model = this._activeModel || 'qwen2.5:7b';
            console.log(`[OMEGA-LLM] Calling Ollama with model: ${model}, messages: ${messages.length}`);
            const result = await this._ollamaGenerate(messages);
            console.log(`[OMEGA-LLM] Response received:`, result ? 'OK' : 'NULL');
            return result;
        } catch (err) {
            console.error(`[OMEGA-LLM] LLM call FAILED:`, err.message, err.stack);
            this.context.addBreadcrumb('agent', `LLM call failed: ${err.message}`, {}, 'error');
            return null;
        }
    }

    // ── Ollama Native (Primary LLM — v5.0) ──────────────────────────
    // Direct /api/chat with native JSON tool calling.
    // Model is set via this._activeModel (propagated from UI dropdown).
    async _ollamaGenerate(messages) {
        const http = require('http');

        const model = this._activeModel || 'qwen2.5:7b';

        // Build Ollama tool declarations from TOOL_REGISTRY
        const { TOOL_REGISTRY } = require('./omega_tools');
        const tools = Object.entries(TOOL_REGISTRY).map(([name, tool]) => {
            const properties = {};
            const required = [];
            for (const [k, v] of Object.entries(tool.args || {})) {
                properties[k] = { type: v.type || 'string', description: v.description || k };
                if (v.required) required.push(k);
            }
            return {
                type: 'function',
                function: {
                    name,
                    description: tool.description,
                    parameters: {
                        type: 'object',
                        properties,
                        required,
                    },
                },
            };
        });

        const payload = JSON.stringify({
            model,
            messages,
            tools,
            stream: false,
            options: { temperature: 0.2, num_predict: 8192 },
        });

        // Ollama Cloud Primary, Local Fallback
        const https = require('https');
        const fs = require('fs');
        const path = require('path');

        function _getOllamaKey() {
            if (process.env.OLLAMA_API_KEY) return process.env.OLLAMA_API_KEY;
            try {
                const envFile = path.join(require('os').homedir(), '.hermes', '.env');
                if (fs.existsSync(envFile)) {
                    const lines = fs.readFileSync(envFile, 'utf-8').split('\n');
                    for (const line of lines) {
                        const m = line.match(/^OLLAMA_API_KEY\s*=\s*(.+)/);
                        if (m) return m[1].trim().replace(/^["']|["']$/g, '');
                    }
                }
            } catch (e) { console.warn('[OMEGA-LLM] Could not read Hermes .env:', e.message); }
            return null;
        }

        const ollamaKey = _getOllamaKey();
        const { cloud: cloudModel, local: localModel } = this._resolveModel(this._activeModel);

        return new Promise((resolve, reject) => {
            // --- Ollama Cloud path ---
            if (ollamaKey) {
                console.log(`[OMEGA-LLM] Ollama Cloud: model=${cloudModel}, msgs=${messages.length}`);
                const cloudPayload = JSON.stringify({
                    model: cloudModel,
                    messages: messages,
                    stream: false,
                    temperature: 0.2,
                    max_tokens: 8192,
                });
                const cloudReq = https.request({
                    hostname: 'ollama.com', port: 443,
                    path: '/v1/chat/completions',
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${ollamaKey}`,
                    },
                    timeout: 180000,
                }, (res) => {
                    let data = '';
                    res.on('data', (c) => data += c);
                    res.on('end', () => {
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.error) {
                                console.error('[OMEGA-LLM] Ollama Cloud error:', parsed.error);
                            } else {
                                const content = parsed.choices?.[0]?.message?.content;
                                if (content && content.trim().length > 0) {
                                    console.log('[OMEGA-LLM] Ollama Cloud OK, length:', content.length);
                                    resolve({ role: 'assistant', content });
                                    return;
                                }
                            }
                        } catch (e) { /* fall through */ }
                        console.warn('[OMEGA-LLM] Ollama Cloud empty/invalid, falling back');
                        _tryLocal();
                    });
                });
                cloudReq.on('error', (e) => {
                    console.warn('[OMEGA-LLM] Ollama Cloud network error:', e.message);
                    _tryLocal();
                });
                cloudReq.on('timeout', () => {
                    cloudReq.destroy();
                    console.warn('[OMEGA-LLM] Ollama Cloud timeout, falling back');
                    _tryLocal();
                });
                cloudReq.write(cloudPayload);
                cloudReq.end();
            } else {
                console.log('[OMEGA-LLM] No OLLAMA_API_KEY, using local Ollama');
                _tryLocal();
            }

            // --- Local Ollama path ---
            function _tryLocal() {
                // Rebuild payload with local-safe model name
                const localPayload = JSON.stringify({
                    model: localModel,
                    messages,
                    tools,
                    stream: false,
                    options: { temperature: 0.2, num_predict: 8192 },
                });
                console.log(`[OMEGA-LLM] Local Ollama: model=${localModel}`);
                const localReq = http.request({
                    hostname: '127.0.0.1', port: 11434,
                    path: '/api/chat', method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    timeout: 180000,
                }, (res) => {
                    let data = '';
                    res.on('data', (c) => data += c);
                    res.on('end', () => {
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.error) {
                                console.error('[OMEGA-LLM] Local Ollama API error:', parsed.error);
                                reject(new Error(`Ollama: ${parsed.error}`));
                                return;
                            }
                            resolve(parsed.message || null);
                        } catch (parseErr) {
                            console.error('[OMEGA-LLM] JSON parse failed:', parseErr.message, 'Raw:', data.substring(0, 200));
                            resolve(null);
                        }
                    });
                });
                localReq.on('error', reject);
                localReq.on('timeout', () => { localReq.destroy(); reject(new Error('Ollama timeout')); });
                localReq.write(localPayload);
                localReq.end();
            }
        });
    }

    // ── Response Parser (v5.0 Native Ollama) ──────────────────────────────
    // Handles Ollama native tool_calls JSON format directly.
    // Input is the full message object from Ollama: { role, content, tool_calls }
    _parseResponse(msgObj) {
        // Handle string input (legacy/fallback)
        if (typeof msgObj === 'string') {
            if (msgObj.trim().length > 0) return { type: 'response', content: msgObj };
            return { type: 'response', content: '(Empty response)' };
        }
        if (!msgObj) return { type: 'response', content: '(No response from model)' };

        // Check for tool_calls (Ollama native OR pre-mapped Hermes)
        if (msgObj.tool_calls && Array.isArray(msgObj.tool_calls) && msgObj.tool_calls.length > 0) {
            const calls = msgObj.tool_calls.map(tc => {
                // Hermes already mapped to internal format — pass through unchanged
                if (tc._native === true && tc.op && tc.tgt) {
                    return tc;
                }
                // Ollama native tool call — convert to internal format
                const fn = tc.function || tc;
                const toolName = fn.name;
                const args = fn.arguments || {};
                return {
                    op: 'REQ',
                    act: 'RUN',
                    tgt: toolName,
                    prm: JSON.stringify(args),
                    bnd: null,
                    rgm: 'SAFE',
                    fal: 'PASS',
                    _native: true,
                    _toolName: toolName,
                    _args: args,
                };
            });
            return { type: 'tools', calls };
        }

        // Plain text response
        const content = msgObj.content || '';
        if (content.trim().length > 0) return { type: 'response', content };

        return { type: 'response', content: '(Empty response from model)' };
    }

    /**
     * v5.0: Clean up chat messages for display.
     * Strips any residual artifacts from the response.
     */
    _sanitizeForChat(text) {
        if (text === null || text === undefined) return '(Task completed — see tool steps above)';

        let clean = text;
        if (typeof clean !== 'string') {
            try {
                clean = JSON.stringify(clean, null, 2);
            } catch(e) {
                clean = String(clean);
            }
        }
        // 0. Strip XML thought tags
        clean = clean.replace(/<thought>[\s\S]*?<\/thought>/gi, '');
        // 1. Strip orphaned code fences
        clean = clean.replace(/^```\s*$/gm, '');
        // 2. Collapse excessive whitespace
        clean = clean.replace(/\n{3,}/g, '\n\n').trim();
        
        if (!clean || clean.length < 10) clean = '(Task completed — all work has been output to files via native tools)';

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
            'conda', 'poetry', 'pipenv', 'uv', 'start', 'invoke-item',
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


    // ── v4.3.19: Parameter parsing for Native Tool Executor ──
    _parsePRM(raw) {
        if (!raw || typeof raw !== 'string') return {};
        // Strip wrapping quotes from LLM output
        let cleaned = raw.trim();
        if ((cleaned.startsWith('"') && cleaned.endsWith('"')) ||
            (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
            cleaned = cleaned.slice(1, -1);
        }
        // Attempt strict JSON parse first
        try {
            const parsed = JSON.parse(cleaned);
            return typeof parsed === 'object' && parsed !== null ? parsed : { value: parsed };
        } catch (_) { /* fall through */ }
        // Try extracting JSON from markdown code blocks
        const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)```/);
        if (codeBlockMatch) {
            try {
                return JSON.parse(codeBlockMatch[1].trim());
            } catch (_) { /* fall through */ }
        }
        // Try key=value parsing (e.g., 'path="/tmp/foo.txt"')
        const kvPairs = {};
        const kvRegex = /(\w+)\s*[=:]\s*"([^"]*)"/g;
        let match;
        while ((match = kvRegex.exec(cleaned)) !== null) {
            kvPairs[match[1]] = match[2];
        }
        if (Object.keys(kvPairs).length > 0) return kvPairs;
        // Last resort: treat as single path/value argument
        return { path: cleaned, value: cleaned };
    }

    // ── Tool Execution (v5.2 — Path 2: Hermes pre-executes) ───────────────────
    // When HermesChannel returns tool_calls with _native=true and _result set,
    // the tools were already executed by Hermes in its subprocess.
    // We skip re-execution and use the pre-computed results directly.
    async _executeToolCalls(calls) {
        const results = [];

        for (const packet of calls) {
            if (this._aborted) {
                results.push({ error: 'Aborted' });
                continue;
            }

            // ── v5.2: Path 2 — Hermes pre-executed this tool ────────────────
            // HermesChannel.completeWithHistory() already ran the tool and captured
            // the result. Use it directly instead of re-executing.
            if (packet._native === true && packet._result !== undefined) {
                const resultText = typeof packet._result === 'string'
                    ? packet._result
                    : JSON.stringify(packet._result);
                const result = {
                    ok: !packet._error,
                    result: resultText,
                    data: resultText,
                    _fromHermes: true,   // tag for debugging/logging
                };
                results.push(result);
                const displayResult = packet._error
                    ? `❌ Hermes error: ${packet._error}`
                    : `✅ Hermes: ${resultText.substring(0, 120)}`;
                this._logStep(`${packet.act}:${packet.tgt}`, packet.prm, result);
                this._emitProgress({ phase: 'tool', tool: `${packet.act}:${packet.tgt}`, args: packet.prm, result: displayResult });
                continue;
            }

            const safety = packet.rgm || SAFETY.SAFE;
            const pseudo_tool_name = `${packet.act}:${packet.tgt}`;

            // ── v4.3.19: SAFE tool whitelist — skip cortex intercept for read-only ops ──
            const CORTEX_SAFE_TOOLS = new Set([
                'RUN:readFile', 'RUN:listDir', 'RUN:search', 'RUN:readDir',
                'RUN:getFileInfo', 'RUN:stat', 'RUN:glob', 'RUN:which',
                'EXT:NET', 'REQ:NET', 'RUN:AST'
            ]);
            const skipCortex = CORTEX_SAFE_TOOLS.has(pseudo_tool_name) ||
                               (safety === SAFETY.SAFE && packet.act !== 'MUT');

            if (!skipCortex) {
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
                                headers: (() => {
                                    const h = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gravity-Omega/4.3' };
                                    // v4.3.18k: Auto-inject auth for known APIs
                                    if (url.includes('api.github.com')) {
                                        try {
                                            const cfg = JSON.parse(fs.readFileSync('C:\\Users\\rlope\\.veritas\\config.json', 'utf8'));
                                            if (cfg.github_token) h['Authorization'] = 'token ' + cfg.github_token;
                                            h['Accept'] = 'application/vnd.github+json';
                                        } catch(e) { /* no config */ }
                                    }
                                    return h;
                                })()
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
                        // v4.3.18l: Sanitize response - strip HTML, cap size, BLOCK VTP injection
                        let text = fetchResult.content || '';
                        // Strip scripts, styles, HTML tags
                        text = text.replace(/<script[\s\S]*?<\/script>/gi, '')
                                   .replace(/<style[\s\S]*?<\/style>/gi, '')
                                   .replace(/<[^>]+>/g, ' ')
                                   .replace(/\s{2,}/g, ' ')
                                   .trim();
                        // SECURITY: Strip any VTP-like patterns from external content
                        text = text.replace(/REQ::/g, '[BLOCKED:REQ]')
                                   .replace(/MUT::/g, '[BLOCKED:MUT]')
                                   .replace(/EXT::/g, '[BLOCKED:EXT]')
                                   .replace(/CREATE::/g, '[BLOCKED:CREATE]')
                                   .replace(/RUN::/g, '[BLOCKED:RUN]')
                                   .replace(/EXEC::/g, '[BLOCKED:EXEC]')
                                   .replace(/\[ACT:/g, '[BLOCKED:ACT]');
                        // Cap response and wrap in boundary markers
                        text = text.substring(0, 8000);
                        text = '[NET_RESPONSE_START]\n' + text + '\n[NET_RESPONSE_END]';
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

                    // v4.3.18p: Fallback — if content is empty but PRM is long, the parse failed
                    // Try to extract content from the raw PRM by skipping the path portion
                    if (prm.length > filePath.length + 10) {
                        const afterPath = prm.substring(prm.indexOf(filePath) + filePath.length);
                        const possibleContent = afterPath.replace(/^[,=:\s"]+/, '').replace(/"$/, '');
                        if (possibleContent.length > 20) {
                            content = possibleContent;
                            console.log('[MUT:AST] Recovered content via fallback extraction:', content.length, 'chars');
                        }
                    }

                    // v4.3.18e: BLOCK empty-content writes â€” these are parse failures, not intentional
                    if (!content && filePath) {
                        console.error('[MUT:AST] BLOCKED: Content is empty for', filePath, 'â€” PRM starts with:', prm.substring(0, 200));
                        results.push({ error: `Empty content for ${filePath} â€” parse failure` });
                        this._logStep(pseudo_tool_name, filePath, { error: 'Empty content â€” parse failure' });
                        continue;
                    }

                    // v4.3.18p: Strip "content=" prefix left by parser
                    if (content.match(/^content[=:]\s*/i)) {
                        content = content.replace(/^content[=:]\s*/i, '');
                        console.log('[MUT:AST] Stripped content= prefix');
                    }

                    // v4.3.18r: Strip triple-quote wrapping from file content
                    // LLM sometimes wraps entire files in """...""" or '''...'''
                    if (content.startsWith('"""') && content.trimEnd().endsWith('"""')) {
                        content = content.slice(3);
                        if (content.trimEnd().endsWith('"""')) {
                            content = content.trimEnd().slice(0, -3);
                        }
                        console.log('[MUT:AST] Stripped triple-quote wrapping');
                    } else if (content.startsWith("'''") && content.trimEnd().endsWith("'''")) {
                        content = content.slice(3);
                        if (content.trimEnd().endsWith("'''")) {
                            content = content.trimEnd().slice(0, -3);
                        }
                        console.log('[MUT:AST] Stripped triple-quote wrapping');
                    }

                    // Resolve relative paths
                    filePath = this._resolveFilePath(filePath);

                    if (filePath) {
                        const dir = path.dirname(filePath);
                        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                        // Unescape common LLM escape sequences
                        // v4.3.18g: Use split/join to unescape LLM sequences (avoids regex escaping hell)
                        // v4.3.18q: Smart unescape — only convert \\n if NO real newlines exist
                        if (!content.includes('\n') && content.includes('\\n')) {
                            content = content.split('\\n').join('\n');
                        }
                        if (!content.includes('\t') && content.includes('\\t')) {
                            content = content.split('\\t').join('\t');
                        }
                        content = content.split("\\'").join("'");
                        content = content.split('\\"').join('"');
                        // v4.3.18p: Fix double-encoded backslashes (LLM sends \\\\path → \\path)
                        if (content.includes('\\\\')) {
                            content = content.split('\\\\').join('\\');
                        }
                        // v4.3.18r: TRUNCATION GUARD — detect incomplete files from LLM output truncation
                        const ext = path.extname(filePath).toLowerCase();
                        if (['.py', '.js', '.html', '.css', '.json'].includes(ext)) {
                            let isTruncated = false;
                            let truncReason = '';
                            if (ext === '.py' || ext === '.js') {
                                const opens = (content.match(/[({\[]/g) || []).length;
                                const closes = (content.match(/[)}\]]/g) || []).length;
                                if (opens - closes > 3) {
                                    isTruncated = true;
                                    truncReason = 'Unbalanced brackets: ' + opens + ' open vs ' + closes + ' close';
                                }
                            }
                            if (ext === '.html' && !content.includes('</html>') && !content.includes('</HTML>')) {
                                isTruncated = true;
                                truncReason = 'Missing closing </html> tag';
                            }
                            if (ext === '.json') {
                                try { JSON.parse(content); } catch(e) {
                                    isTruncated = true;
                                    truncReason = 'Invalid JSON: ' + e.message;
                                }
                            }
                            if (isTruncated) {
                                console.error('[MUT:AST] TRUNCATION BLOCKED: ' + filePath + ' — ' + truncReason);
                                const truncResult = { error: 'File truncated (' + truncReason + '). Split into files under 150 lines.' };
                                results.push(truncResult);
                                this._logStep(pseudo_tool_name, filePath, truncResult);
                                continue;
                            }
                        }
                        // v4.3.18e: Shrink protection - refuse to overwrite larger files with tiny content â€” refuse to overwrite larger files with tiny content
                        if (fs.existsSync(filePath)) {
                            const existingSize = fs.statSync(filePath).size;
                            const newSize = Buffer.byteLength(content, 'utf8');
                            if (existingSize > 200 && newSize < existingSize * 0.15) {
                                console.warn(`[MUT:AST] SHRINK BLOCKED: ${filePath} (${existingSize}b â†’ ${newSize}b = ${Math.round(newSize/existingSize*100)}%). Keeping existing content.`);
                                results.push({ ok: true, message: `File preserved (shrink protection): ${filePath}` });
                                this._logStep(pseudo_tool_name, filePath, { ok: true, message: 'Shrink protection â€” kept existing' });
                                continue;
                            }
                        }
                        fs.writeFileSync(filePath, content, 'utf8');
                        const result = { ok: true, message: `File written: ${filePath}`, path: filePath };
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
                    let cmd = prm.replace(/^\"/, '').replace(/\"$/, '').trim();
                    // v4.3.18p: Strip powershell.exe wrapper — exec() already uses shell: true (PowerShell)
                    cmd = cmd.replace(/^powershell(?:\.exe)?\s+(?:-(?:Command|c)\s+)?/i, '')
                             .replace(/^"/, '').replace(/"$/, '')
                             .replace(/^'/, '').replace(/'$/, '')  // v4.3.18r: Strip leaked single quotes
                             .trim();
                    // Also detect New-Item and convert to fs.mkdirSync
                    const newItemMatch = cmd.match(/New-Item\s+.*?-Path\s+['"](.*?)['"]/i);
                    if (newItemMatch && cmd.includes('-ItemType Directory')) {
                        const dirPath = this._resolveFilePath(newItemMatch[1]);
                        fs.mkdirSync(dirPath, { recursive: true });
                        const result = { ok: true, message: 'Directory created: ' + dirPath };
                        results.push(result);
                        this._logStep(pseudo_tool_name, packet.prm, result);
                        continue;
                    }
                    if (!this._isDestructiveCommand(cmd)) {
                        console.log('[AUTO-EXEC] Non-destructive SYS:', cmd.substring(0, 100));
                        const { exec } = require('child_process');
                        // v4.3.18i: Extract CWD from absolute paths in the command
                        let execCwd = process.cwd();
                        const absPathMatch = cmd.match(/["']?([A-Za-z]:\\[^"'\s]+\.\w+)["']?/);
                        if (absPathMatch) {
                            const scriptDir = require('path').dirname(absPathMatch[1]);
                            if (fs.existsSync(scriptDir)) execCwd = scriptDir;
                        }
                        const output = await new Promise((resolve, reject) => {
                            exec(cmd, { encoding: 'utf8', timeout: 120000, cwd: execCwd, shell: true }, (err, stdout, stderr) => {
                                if (err) reject(Object.assign(err, { stderr }));
                                else resolve(stdout + (stderr ? '\nSTDERR: ' + stderr : ''));
                            });
                        });
                        // v4.3.18o: Strip HTML from SYS output (catches curl returning error pages)
                        let cleanOutput = output;
                        if (cleanOutput.includes('<html') || cleanOutput.includes('<!doctype') || cleanOutput.includes('<!DOCTYPE')) {
                            cleanOutput = cleanOutput.replace(/<script[\s\S]*?<\/script>/gi, '')
                                .replace(/<style[\s\S]*?<\/style>/gi, '')
                                .replace(/<[^>]+>/g, ' ')
                                .replace(/\s{2,}/g, ' ')
                                .trim();
                        }
                        const result = { ok: true, output: cleanOutput.substring(0, 5000), message: `Executed: ${cmd.substring(0, 100)}` };
                        results.push(result);
                        this._logStep(pseudo_tool_name, packet.prm, result);
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

            // Native Node Tool Executor Intercept
            if (TOOL_REGISTRY[packet.tgt] && packet.act === 'RUN') {
                try {
                    this._emitProgress({ phase: 'tool', tool: pseudo_tool_name, args: packet.prm });
                    
                    const jsonArgs = this._parsePRM(packet.prm || '');
                    if (!this.executor) this.executor = new ToolExecutor({ bridge: this.bridge });
                    const result = await this.executor.execute(packet.tgt, jsonArgs);
                    
                    results.push(result);
                    this._logStep(pseudo_tool_name, packet.prm, { ok: true, result });
                    await this.hooks.fire('on_gate_result', { tool: pseudo_tool_name, safety: 'SAFE', verdict: 'AUTO_APPROVED' });
                } catch (err) {
                    results.push({ error: err.message });
                    this._logStep(pseudo_tool_name, packet.prm, { error: err.message });
                }
                continue;
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
        this._emitProgress({ phase: 'tool_done', tool, args: result || args, ok: !result?.error, totalSteps: this._stepLog.length });
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
                } else if (TOOL_REGISTRY[packet.tgt] && packet.act === 'RUN') {
                    console.log('[APPROVE] Running TOOL_REGISTRY natively:', pseudo);
                    if (!this.executor) this.executor = new ToolExecutor({ bridge: this.bridge });
                    const jsonArgs = this._parsePRM(packet.prm || '');
                    result = await this.executor.execute(packet.tgt, jsonArgs);
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
        this._running = true;
        this._aborted = false;

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

        // Re-enter the agentic reasoning loop (use module-level MAX_ITERATIONS)
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
                    let results;
                    try {
                        results = await this._executeToolCalls(toolCalls);
                    } catch (err) {
                        messages.push({ role: 'user', content: `Tool execution failed: ${err.message}. Please correct the tool call syntax and try again.` });
                        continue;
                    }

                    const resultSummary = results.map((r, i) => {
                        const call = toolCalls[i];
                        const status = r.error ? '❌ ERROR' : '✅ OK';
                        const output = r.error || JSON.stringify(r.result || r, null, 2);
                        const t = output.length > 2000 ? output.substring(0, 2000) + '\n... (truncated)' : output;
                        return `### ${call.tool} [${status}]\n\`\`\`\n${t}\n\`\`\``;
                    }).join('\n\n');

                    messages.push({ role: 'assistant', content: typeof llmResponse === 'string' ? llmResponse : JSON.stringify(llmResponse) });
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
        } finally {
            this._running = false;
        }

        // Emit the continuation response to the renderer
        if (finalResponse) {
            this.bridge.emit('continuation', finalResponse);
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

    // v5.2: Model name resolver — maps UI/friendly names to exact backend names.
    _resolveModel(raw) {
        if (!raw) raw = this._activeModel || 'qwen3:8b';
        const key = raw.toLowerCase().trim().replace(/\s+/g, '-').replace(/-+$/g, '').trim();
        const CLOUD_MAP = {
            'qwen3:8b': 'deepseek-v3.1:671b',
            'qwen2.5:7b': 'deepseek-v3.1:671b',
            'qwen2.5:14b': 'deepseek-v3.1:671b',
            'gemini-3-flash-preview': 'gemini-3-flash-preview',
            'gemini-3-flash': 'gemini-3-flash-preview',
            'deepseek-v3.1:671b': 'deepseek-v3.1:671b',
            'deepseek-v3.1': 'deepseek-v3.1:671b',
        };
        const LOCAL_MAP = {
            'qwen3:8b': 'qwen3:8b',
            'qwen2.5:7b': 'qwen2.5:7b',
            'qwen2.5:14b': 'qwen2.5:14b',
            'deepseek-v3.1:671b': 'qwen3:8b',
            'deepseek-v3.1': 'qwen3:8b',
            'gemini-3-flash-preview': 'qwen3:8b',
        };
        return {
            raw: raw,
            cloud: CLOUD_MAP[key] || CLOUD_MAP['qwen3:8b'],
            local: LOCAL_MAP[key] || LOCAL_MAP['qwen3:8b'],
        };
    }
}

module.exports = { OmegaAgent };
