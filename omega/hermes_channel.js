/**
 * HERMES CHANNEL v2.0 — Hermes ACP Adapter Bridge for Gravity Omega
 *
 * Spawns the Hermes Agent ACP adapter as a stdio JSON-RPC subprocess,
 * then proxies Omega LLM calls through it. This replaces the Ollama
 * backend when the user switches to Hermes mode.
 *
 * Architecture:
 *   OmegaAgent._llmCall()
 *     → HermesChannel.complete()       ← streams text + tool calls, returns structured response
 *     → Hermes ACP subprocess           ← python -m acp_adapter.entry (JSON-RPC over stdio)
 *       → Hermes AIAgent               ← full Hermes tool suite + LLM (Ollama Cloud)
 *
 * Session model: one ACP session per Omega conversation thread.
 * The subprocess stays alive across calls — sessions are persisted in SQLite.
 *
 * Tool call flow (Path 2 — Hermes executes tools, Omega displays):
 *   1. Hermes calls a tool  → agent/tool_call_start notification arrives
 *   2. Hermes tool finishes  → agent/tool_call_update (status=completed) notification arrives
 *   3. Omega receives both  → displays them live to the user in the step log
 *   4. Hermes streams final text → agent/message_chunk notifications arrive
 *   5. Omega accumulates everything until stop_reason in final response
 *   6. _hermesGenerate returns structured response with tool_calls + content
 *   7. OmegaAgent._parseResponse sees tool_calls → executes via _executeToolCalls
 *   8. Results fed back to Hermes via completeWithHistory() in next loop iteration
 *
 * v2.0: Full tool call streaming support (Path 2), fixed notification method names,
 *       fixed streaming race condition (promise resolves only after stream ends).
 */
'use strict';

const { spawn } = require('child_process');
const EventEmitter = require('events');

// ── Protocol constants ────────────────────────────────────────────────────────
const ACP_JSONRPC_VERSION = '2.0';

// ACP method names (Client → Server)
const METHOD_INITIALIZE    = 'initialize';
const METHOD_NEW_SESSION    = 'session/new';
const METHOD_PROMPT         = 'prompt';
const METHOD_CANCEL         = 'cancel';
const METHOD_LIST_SESSIONS  = 'sessions/list';
const METHOD_HEARTBEAT      = 'sessions/heartbeat';

// ACP notification method names (Server → Client) — these are the
// `session_update` discriminator values in the ACP SessionNotification union
const MSG_AGENT_MESSAGE_CHUNK     = 'agent_message_chunk';
const MSG_AGENT_THOUGHT_CHUNK     = 'agent_thought_chunk';
const MSG_TOOL_CALL_START        = 'tool_call_start';
const MSG_TOOL_CALL_UPDATE       = 'tool_call_update';
const MSG_SESSION_UPDATE          = 'session/update';
const MSG_AVAILABLE_COMMANDS     = 'available_commands_update';
const MSG_AGENT_MESSAGE_TEXT     = 'agent_message_text';   // legacy alias (unused)

// ── Hermes ACP adapter entry point ────────────────────────────────────────────
function _hermesCommand() {
    // Route via cmd.exe (which always has Windows system32 in PATH) → wsl
    // Direct spawn of 'wsl' fails because the Node process can't resolve it.
    // cmd.exe /c wsl works because Windows resolves it via the Windows PATH.
    return {
        cmd: 'cmd.exe',
        args: ['/c', 'wsl', '--', 'bash', '-c',
            'source ~/.hermes/hermes-agent/venv/bin/activate 2>/dev/null || true; ' +
            'cd ~/.hermes/hermes-agent && python3 -m acp_adapter.entry'
        ],
    };
}

// ── JSON-RPC frame helpers ─────────────────────────────────────────────────────
function rpcRequest(id, method, params) {
    return JSON.stringify({
        jsonrpc: ACP_JSONRPC_VERSION,
        id,
        method,
        params,
    });
}

function rpcResponse(id, result) {
    return JSON.stringify({
        jsonrpc: ACP_JSONRPC_VERSION,
        id,
        result,
    });
}

function rpcError(id, code, message) {
    return JSON.stringify({
        jsonrpc: ACP_JSONRPC_VERSION,
        id,
        error: { code, message },
    });
}

// ── Tool call helpers ──────────────────────────────────────────────────────────

/**
 * Build an Omega-compatible tool call object from Hermes ACP tool data.
 * Returns null if the tool kind is not something Omega can display.
 */
function _buildOmegaToolCall(toolName, toolCallId, rawArgs, kind) {
    const OmegaToolMap = {
        // ━━ ToolKind → Omega tool (primary mapping, sent by ACP adapter)
        read:       'openFile',
        edit:       'writeFile',
        search:     'searchFiles',
        execute:    'exec',
        fetch:      'webFetch',
        other:      'exec',

        // ━━ Hermes tool name → Omega tool (fallback if toolName is known)
        read_file:      'openFile',
        write_file:     'writeFile',
        patch:          'editFile',
        search_files:   'searchFiles',
        terminal:       'exec',
        process:        'exec',
        execute_code:   'exec',
        web_search:     'webFetch',
        web_extract:    'webFetch',
        browser_navigate:   'browser',
        browser_snapshot:   'browser',
        browser_click:      'browser',
        browser_type:       'browser',
        browser:            'browser',
    };

    const omegaName = OmegaToolMap[kind] || OmegaToolMap[toolName] || 'exec';

    return {
        tgt:    omegaName,           // Omega tool target name
        name:   omegaName,
        id:     toolCallId,
        tool:   omegaName,
        args:   rawArgs || {},
    };
}

/**
 * Parse Hermes tool arguments from an ACP tool start notification.
 * ACP sends raw_input as a dict — extract what we need.
 */
function _extractToolArgs(rawInput) {
    if (!rawInput || typeof rawInput !== 'object') return {};
    // Forward raw arguments as-is — Omega's ToolExecutor handles them
    return rawInput;
}

// ── HermesChannel ──────────────────────────────────────────────────────────────
class HermesChannel extends EventEmitter {
    /**
     * @param {object} opts
     * @param {string} opts.cwd  Working directory for the ACP session (default: gravity-omega-v2)
     */
    constructor({ cwd } = {}) {
        super();
        this._cwd = cwd || '/home/veritas/gravity-omega-v2';
        this._proc = null;
        this._ready = false;
        this._pending = new Map();    // id → { resolve, reject, method }
        this._sessionId = null;
        this._idCounter = 1;
        this._buf = '';              // partial JSON lines from stdout

        // Stream accumulation — cleared on each completeWithHistory() call
        this._streamBuffer = '';     // final text content
        this._stopReason = null;     // 'end_turn', 'max_iterations', etc.
        this._toolCalls = [];        // accumulated tool calls (in flight)
        this._completedTools = {};   // toolCallId → completed result

        // Progress callbacks for the agent loop
        this.onThinking = null;      // (text: string) => void
        this.onToolProgress = null;  // (toolName, input, output) => void
        this.onStep = null;          // (stepText: string) => void
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    /**
     * Start the Hermes ACP subprocess and establish a session.
     * Safe to call multiple times — no-op if already running.
     */
    async start() {
        if (this._proc) return;

        const { cmd, args } = _hermesCommand();
        console.log('[HermesChannel] Spawning ACP adapter:', cmd, args.join(' '));

        this._proc = spawn(cmd, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            env: { ...process.env },
            cwd: this._cwd,
            windowsHide: false,
        });

        this._proc.stdout.on('data', (d) => this._onStdout(d.toString()));
        this._proc.stderr.on('data', (d) => {
            const txt = d.toString().trim();
            if (txt) console.log('[HermesChannel:stderr]', txt);
        });
        this._proc.on('exit', (code) => {
            console.log('[HermesChannel] Process exited with code', code);
            if (this._pinger) { clearInterval(this._pinger); this._pinger = null; }
            this._proc = null;
            this._ready = false;
            this._sessionId = null;
            this.emit('exit', code);
        });
        this._proc.on('error', (err) => {
            console.error('[HermesChannel] Spawn error:', err.message);
            this.emit('error', err);
        });

        // Wait for initialize + new_session to complete
        await this._waitReady();

        // Pre-warm the adapter with a heartbeat ping so the first real prompt
        // gets a cache-hit agent (not a cold-creation stall).
        this._pinger = setInterval(() => {
            if (this._proc && this._ready) {
                this.ping().catch(() => {});
            }
        }, 30_000);
    }

    async _waitReady() {
        const initResult = await this._send(METHOD_INITIALIZE, {
            protocol_version: 1,
            client_info: { name: 'gravity-omega', version: '2.0' },
        });

        // Create a new session for this conversation thread
        // cwd: must be an absolute path; mcp_servers: required even if empty
        const sessionResult = await this._send(METHOD_NEW_SESSION, {
            cwd: '/home/veritas',
            mcp_servers: [],
        });

        // sessionId comes back as camelCase from the ACP JSON-RPC response
        this._sessionId = sessionResult.sessionId;
        this._ready = true;
        console.log('[HermesChannel] Ready — session:', this._sessionId);
    }

    /** Stop the subprocess. */
    stop() {
        if (this._pinger) { clearInterval(this._pinger); this._pinger = null; }
        if (this._proc) {
            this._proc.kill('SIGTERM');
            this._proc = null;
        }
        this._ready = false;
        this._sessionId = null;
        this._pending.clear();
    }

    /**
     * Probe adapter health via sessions/heartbeat.
     * Returns { ok, uptime, model, cache, sessions, prewarm } or {} on failure.
     * Uses a dedicated RPC call so it never collides with live prompt calls.
     */
    async ping() {
        if (!this._proc || !this._ready) return {};
        try {
            return await this._send(METHOD_HEARTBEAT, {}, 10_000);
        } catch (_) {
            return {};
        }
    }

    // ── Core API ───────────────────────────────────────────────────────────────

    /**
     * Send a text prompt to Hermes and return the final response string.
     * Uses the ACP prompt/1 method with streaming text accumulation.
     *
     * @param {string} userText
     * @returns {Promise<string>} final response text
     * @deprecated Use completeWithHistory() for full tool call support
     */
    async complete(userText) {
        const result = await this.completeWithHistory([
            { role: 'user', content: userText }
        ]);
        return result.text;
    }

    /**
     * Full prompt with explicit message history.
     * Messages is an array of { role: 'user'|'assistant'|'system', content: string }.
     *
     * This is the primary entry point for OmegaAgent._hermesGenerate().
     * It streams all events (text chunks, tool starts, tool completions) and
     * accumulates them internally. Returns when Hermes sends the final response.
     *
     * Returns an Omega-compatible message object:
     *   { role: 'assistant', content: string, tool_calls: [...] }
     *
     * @param {Array<{role:string,content:string}>} messages
     * @returns {Promise<{text: string, stop_reason: string, tool_calls: Array}>}
     */
    async completeWithHistory(messages) {
        if (!this._ready || !this._sessionId) {
            throw new Error('[HermesChannel] Not ready — call start() first');
        }

        // Clear stream state for a new run
        this._streamBuffer = '';
        this._stopReason = null;
        this._toolCalls = [];
        this._completedTools = {};

        const prompt = messages.map((m) => ({
            type: 'text',
            text: `${m.role}: ${m.content}`,
        }));

        // ACP method name is 'session/prompt' (from AGENT_METHODS["session_prompt"])
        const result = await this._send('session/prompt', {
            prompt,
            session_id: this._sessionId,
        });

        // Merge accumulated tool calls with their completed results
        const toolCalls = this._toolCalls.map((tc) => {
            const completed = this._completedTools[tc.id];
            if (completed) {
                return {
                    ...tc,
                    result: completed.result,
                    error: completed.error,
                };
            }
            return tc;
        });

        const safeResult = result || {};
        return {
            text: this._streamBuffer || safeResult.text || '',
            stop_reason: this._stopReason || safeResult.stop_reason || 'end_turn',
            tool_calls: toolCalls,
        };
    }

    // ── JSON-RPC send/recv ─────────────────────────────────────────────────────

    _nextId() {
        return this._idCounter++;
    }

    /**
     * Send a JSON-RPC request and wait for the response.
     * For prompt(), this resolves only AFTER streaming is complete
     * (server sends the final response object after all notifications).
     * @returns {Promise<any>}
     */
    _send(method, params, timeoutMs = 120_000) {
        return this._sendStreaming(method, params, timeoutMs).promise;
    }

    /**
     * Low-level: send a streaming request and get back a pending request ID + promise.
     * The promise resolves when the server sends the matching JSON-RPC response
     * (after all streamed notifications have been processed).
     * @returns {{ id: number, promise: Promise<any> }}
     */
    _sendStreaming(method, params, timeoutMs = 120_000) {
        if (!this._proc || !this._proc.stdin) {
            throw new Error('HermesChannel subprocess not running');
        }

        const id = this._nextId();
        const promise = new Promise((resolve, reject) => {
            this._pending.set(id, {
                resolve,
                reject,
                method,
                isStreaming: true,
                response: null,
                streamingDone: false,
            });
        });

        this._proc.stdin.write(rpcRequest(id, method, params) + '\n');

        // Timeout after `timeoutMs` milliseconds
        const timer = setTimeout(() => {
            if (this._pending.has(id)) {
                this._pending.delete(id);
                reject(new Error(`[HermesChannel] ${method} timed out after ${timeoutMs}ms`));
            }
        }, timeoutMs);

        const entry = this._pending.get(id);
        entry.timer = timer;

        return { id, promise };
    }

    _resolve(id, result) {
        const pending = this._pending.get(id);
        if (!pending) return;
        clearTimeout(pending.timer);
        this._pending.delete(id);
        // For streaming requests (session/prompt), the response frame arrives here AFTER
        // all notifications have been processed in the same _onStdout event chain.
        // Resolving here is correct — all streamed content has been accumulated.
        pending.resolve(result);
    }

    _reject(id, code, message) {
        const pending = this._pending.get(id);
        if (!pending) return;
        clearTimeout(pending.timer);
        this._pending.delete(id);
        pending.reject(new Error(`[HermesChannel] RPC error ${code}: ${message}`));
    }

    // ── Output parser ──────────────────────────────────────────────────────────

    _onStdout(data) {
        this._buf += data;
        const lines = this._buf.split('\n');
        // Keep the last (potentially partial) line in the buffer
        this._buf = lines.pop();

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) continue;

            let msg;
            try {
                msg = JSON.parse(line);
            } catch {
                // Not JSON — might be a log line from the subprocess
                console.log('[HermesChannel:stdout]', line);
                continue;
            }

            this._handleMessage(msg);
        }
    }

    _handleMessage(msg) {
        // Response (has id) — resolve the pending promise
        if (msg.id !== undefined) {
            if (msg.error) {
                this._reject(msg.id, msg.error.code || -1, msg.error.message || 'Unknown error');
            } else {
                this._resolve(msg.id, msg.result);
            }
            return;
        }

        // Notification (no id) — route by session_update discriminator
        if (!msg.method || !msg.params) return;
        this._handleNotification(msg.method, msg.params);
    }

    _handleNotification(method, params) {
        // ACP stdio sends camelCase field aliases by default (by_alias=True).
        // params is the SessionNotification params: { sessionId, update: {...} }
        // The update object has sessionUpdate as discriminator (camelCase).
        const update = params.update || params;
        const sessionUpdateType = update.sessionUpdate || params.sessionUpdate;

        switch (sessionUpdateType) {
            // ── Text streaming ─────────────────────────────────────────────
            case 'agent_message_chunk': {
                // AgentMessageChunk.content is a ContentChunk with a .text field
                const content = update.content;
                const text = (content && (content.text || content.content)) ||
                             update.text || update.content || '';
                this._streamBuffer += text;
                break;
            }

            case 'agent_message_text':
            case 'agent_thought_chunk': {
                // agent/thought_chunk — Hermes internal reasoning
                const text = update.thinking || update.text || update.content || '';
                if (this.onThinking) this.onThinking(text);
                break;
            }

            // ── Tool calls ─────────────────────────────────────────────
            case 'tool_call':
            case 'tool_call_start':
            case 'tool_call_update': {
                // ToolCallStart (tool_call) or ToolCallProgress (tool_call_update)
                // ACP schema uses camelCase aliases: toolCallId, toolName, rawInput, rawOutput
                const toolCallId = update.toolCallId || update.id || '';
                const toolName   = update.name || update.toolName || '?';
                const rawArgs    = update.rawInput || update.arguments || {};
                const kind       = update.kind || 'other';
                const status     = update.status;  // 'completed', 'error', or in-progress

                if (status === 'completed' || status === 'error') {
                    // Tool has finished — store the result
                    const rawOutput  = update.rawOutput || update.result || '';
                    const resultText = (rawOutput && (rawOutput.text || rawOutput.content)) || rawOutput || '';
                    this._completedTools[toolCallId] = {
                        result: resultText,
                        error: status === 'error' ? resultText : null,
                    };
                    if (this.onToolProgress) {
                        const display = status === 'error'
                            ? `❌ ERROR: ${resultText}`
                            : `✅ ${resultText}`;
                        this.onToolProgress(toolName, JSON.stringify(rawArgs), display);
                    }
                } else {
                    // Tool start — add to in-flight list
                    const omegaTool = _buildOmegaToolCall(toolName, toolCallId, rawArgs, kind);
                    // Avoid duplicates if tool_call fires start+progress together
                    const existing = this._toolCalls.findIndex(t => t.id === toolCallId);
                    if (existing >= 0) {
                        this._toolCalls[existing] = omegaTool;
                    } else {
                        this._toolCalls.push(omegaTool);
                    }
                    if (this.onToolProgress) {
                        this.onToolProgress(toolName, JSON.stringify(rawArgs), '[running...]');
                    }
                }
                break;
            }

            // ── Session / state updates ────────────────────────────────
            case 'available_commands_update': {
                break;
            }

            case 'session_update':
            default: {
                // Silently ignore unknown session updates
                break;
            }
        }
    }
}

module.exports = { HermesChannel };
