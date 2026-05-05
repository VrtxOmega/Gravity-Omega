/**
 * omega_mcp_server.js — MCP Server for Gravity Omega IDE
 *
 * Exposes ALL Gravity Omega IDE capabilities as MCP tools over HTTP+SSE.
 * Hermes (or any MCP client) connects → calls tools → triggers NATIVE IDE behavior:
 *   Monaco editor opens, PTY terminals execute, Puppeteer navigates, files mutate.
 *
 * Runs INSIDE the Electron main process — has direct access to mainWindow,
 * terminals, browser, bridge, and agent instances.
 *
 * Mount: require('./omega/omega_mcp_server').startServer({ mainWindow, terminals, browser, bridge, agent })
 */
'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const os = require('os');
const { EventEmitter } = require('events');

const PROTOCOL_VERSION = '2024-11-05';
const SERVER_NAME = 'gravity-omega-ide';
const SERVER_VERSION = '2.1.1';
const SSE_PORT = process.env.MCP_PORT || 3002;
const MAX_BODY_BYTES = 5 * 1024 * 1024;   // 5 MB request body limit
const MAX_SESSIONS = 20;                   // prevent connection exhaustion
const SESSION_MAX_AGE_MS = 4 * 3600000;    // 4 hours max session lifetime
const MAX_TERMINALS = 10;                  // prevent PTY exhaustion

// ── Injected references (set by startServer) ─────────────────────────────
let _ctx = {
    getWindow: () => null,
    terminals: null,
    browser: null,
    bridge: null,
    agent: null,
    ptyModule: null,
    terminalCounter: { value: 1000 },
};

// Stateful shell session (persistent cwd across calls)
let _shellCwd = null;

// Terminal output buffers (keyed by terminal_id)
const _termOutputBuffers = new Map();

// ── SSE Transport (hardened) ─────────────────────────────────────────────
class SseTransport extends EventEmitter {
    constructor(req, res) {
        super();
        this.req = req;
        this.res = res;
        this.sessionId = Math.random().toString(36).slice(2) + Date.now().toString(36);
        this.closed = false;
        this.createdAt = Date.now();
        this._pendingCalls = 0;  // track in-flight tool calls

        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        });
        this.sendEvent('endpoint', `/messages?session_id=${this.sessionId}`);

        req.on('close', () => this.close());
        req.on('error', () => this.close());

        // SSE keep-alive heartbeat every 15s
        this._heartbeat = setInterval(() => {
            if (this.closed) { clearInterval(this._heartbeat); return; }
            try { this.res.write(': keepalive\n\n'); }
            catch { this.close(); }  // socket gone — clean up
        }, 15000);

        // Max session age guard
        this._maxAgeTimer = setTimeout(() => {
            console.log(`[MCP] Session ${this.sessionId} expired (max age)`);
            this.close();
        }, SESSION_MAX_AGE_MS);
    }

    sendEvent(event, data) {
        if (this.closed) return false;
        try {
            this.res.write(`event: ${event}\ndata: ${data}\n\n`);
            return true;
        } catch {
            this.close();
            return false;
        }
    }

    sendMessage(msg) {
        if (msg != null) this.sendEvent('message', JSON.stringify(msg));
    }

    close() {
        if (this.closed) return;
        this.closed = true;
        if (this._heartbeat) { clearInterval(this._heartbeat); this._heartbeat = null; }
        if (this._maxAgeTimer) { clearTimeout(this._maxAgeTimer); this._maxAgeTimer = null; }
        try { this.res.end(); } catch {}
        this.emit('close');
    }
}

const sessions = new Map();

// ── Tool Definitions ─────────────────────────────────────────────────────
const TOOLS = [
    // ── File Operations ──────────────────────────────────────
    {
        name: 'gravity_read_file',
        description: 'Read file contents with optional line range.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string', description: 'Absolute file path' },
                offset: { type: 'number', description: 'Start line (1-indexed)', default: 1 },
                limit: { type: 'number', description: 'Max lines to return', default: 500 }
            },
            required: ['path']
        }
    },
    {
        name: 'gravity_write_file',
        description: 'Write content to a file, creating parent directories. Opens result in Monaco editor.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string' },
                content: { type: 'string' }
            },
            required: ['path', 'content']
        }
    },
    {
        name: 'gravity_patch_file',
        description: 'Find-and-replace patch on a file.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string' },
                old_string: { type: 'string' },
                new_string: { type: 'string' }
            },
            required: ['path', 'old_string', 'new_string']
        }
    },
    {
        name: 'gravity_list_dir',
        description: 'List directory entries with type and size.',
        inputSchema: {
            type: 'object',
            properties: { path: { type: 'string', default: '.' } }
        }
    },
    {
        name: 'gravity_file_exists',
        description: 'Check if a file or directory exists.',
        inputSchema: {
            type: 'object',
            properties: { path: { type: 'string' } },
            required: ['path']
        }
    },
    {
        name: 'gravity_mkdir',
        description: 'Create a directory (recursive).',
        inputSchema: {
            type: 'object',
            properties: { path: { type: 'string' } },
            required: ['path']
        }
    },
    {
        name: 'gravity_delete',
        description: 'Delete a file or directory.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string' },
                recursive: { type: 'boolean', default: false }
            },
            required: ['path']
        }
    },
    {
        name: 'gravity_rename',
        description: 'Rename or move a file.',
        inputSchema: {
            type: 'object',
            properties: {
                old_path: { type: 'string' },
                new_path: { type: 'string' }
            },
            required: ['old_path', 'new_path']
        }
    },
    {
        name: 'gravity_open_in_editor',
        description: 'Open a file in the Monaco editor inside Gravity Omega IDE.',
        inputSchema: {
            type: 'object',
            properties: { path: { type: 'string' } },
            required: ['path']
        }
    },
    // ── Terminal ──────────────────────────────────────────────
    {
        name: 'gravity_terminal_create',
        description: 'Create a new PTY terminal in the IDE. Returns terminal ID.',
        inputSchema: { type: 'object', properties: {} }
    },
    {
        name: 'gravity_terminal_exec',
        description: 'Execute a command in a PTY terminal and return captured output (waits for output to settle).',
        inputSchema: {
            type: 'object',
            properties: {
                terminal_id: { type: 'string' },
                command: { type: 'string' },
                wait_ms: { type: 'number', description: 'Milliseconds to wait for output (default 3000, max 30000)', default: 3000 }
            },
            required: ['terminal_id', 'command']
        }
    },
    {
        name: 'gravity_terminal_kill',
        description: 'Kill a PTY terminal.',
        inputSchema: {
            type: 'object',
            properties: { terminal_id: { type: 'string' } },
            required: ['terminal_id']
        }
    },

    // ── Browser ──────────────────────────────────────────────
    {
        name: 'gravity_browser_navigate',
        description: 'Navigate the IDE embedded browser (Puppeteer) to a URL.',
        inputSchema: {
            type: 'object',
            properties: { url: { type: 'string' } },
            required: ['url']
        }
    },
    {
        name: 'gravity_browser_screenshot',
        description: 'Take a screenshot of the current browser page.',
        inputSchema: {
            type: 'object',
            properties: { name: { type: 'string', default: 'screenshot' } }
        }
    },
    {
        name: 'gravity_browser_close',
        description: 'Close the IDE embedded browser.',
        inputSchema: { type: 'object', properties: {} }
    },
    {
        name: 'gravity_browser_task',
        description: 'Execute a multi-step browser automation task (navigate, click, type, extract).',
        inputSchema: {
            type: 'object',
            properties: {
                steps: {
                    type: 'array',
                    description: 'Array of step objects: { action: "navigate"|"click"|"type"|"screenshot"|"extract", selector?: string, url?: string, text?: string }'
                }
            },
            required: ['steps']
        }
    },
    // ── Shell / CWD ──────────────────────────────────────────
    {
        name: 'gravity_cwd',
        description: 'Get or set the stateful working directory for shell commands.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string', description: 'Set cwd to this path (omit to just read current cwd)' }
            }
        }
    },
    {
        name: 'gravity_execute_command',
        description: 'Execute a shell command with persistent cwd and return stdout/stderr.',
        inputSchema: {
            type: 'object',
            properties: {
                command: { type: 'string' },
                cwd: { type: 'string', description: 'Working directory (overrides stateful cwd)' },
                timeout: { type: 'number', default: 60 }
            },
            required: ['command']
        }
    },
    // ── System ───────────────────────────────────────────────
    {
        name: 'gravity_hardware_info',
        description: 'Get CPU, memory, GPU, and system info.',
        inputSchema: { type: 'object', properties: {} }
    },
    // ── Agent ────────────────────────────────────────────────
    {
        name: 'gravity_agent_chat',
        description: 'Send a message through the Gravity Omega agentic loop (Gemini/Ollama).',
        inputSchema: {
            type: 'object',
            properties: {
                message: { type: 'string' },
                model: { type: 'string', default: 'gemini' }
            },
            required: ['message']
        }
    },
    {
        name: 'gravity_agent_status',
        description: 'Get the current agent status.',
        inputSchema: { type: 'object', properties: {} }
    },
    // ── Backend ──────────────────────────────────────────────
    {
        name: 'gravity_backend_status',
        description: 'Get Python backend (Flask) connection status.',
        inputSchema: { type: 'object', properties: {} }
    },
    {
        name: 'gravity_backend_execute',
        description: 'Execute a backend module by ID.',
        inputSchema: {
            type: 'object',
            properties: {
                module_id: { type: 'string' },
                args: { type: 'object', default: {} }
            },
            required: ['module_id']
        }
    },
    // ── Upload / Image Gen / VERITAS ─────────────────────────
    {
        name: 'gravity_upload_file',
        description: 'Copy/upload a local file to a target destination path.',
        inputSchema: {
            type: 'object',
            properties: {
                source: { type: 'string', description: 'Source file path' },
                dest: { type: 'string', description: 'Destination file path' }
            },
            required: ['source', 'dest']
        }
    },
    {
        name: 'gravity_generate_image',
        description: 'Generate an image via backend AI (Ollama vision or Stable Diffusion).',
        inputSchema: {
            type: 'object',
            properties: {
                prompt: { type: 'string' },
                output_path: { type: 'string', description: 'Where to save the image' },
                width: { type: 'number', default: 512 },
                height: { type: 'number', default: 512 }
            },
            required: ['prompt', 'output_path']
        }
    },
    {
        name: 'gravity_assess_file',
        description: 'Run VERITAS pipeline assessment on a file.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string' },
                mode: { type: 'string', description: 'veritas or sandbox', default: 'veritas' }
            },
            required: ['path']
        }
    },
    // ── Code Intelligence ────────────────────────────────────
    {
        name: 'gravity_find_files',
        description: 'Find files matching a glob pattern recursively.',
        inputSchema: {
            type: 'object',
            properties: {
                directory: { type: 'string' },
                pattern: { type: 'string', description: 'Glob pattern (e.g. *.py, *.js)' }
            },
            required: ['directory', 'pattern']
        }
    },
    {
        name: 'gravity_grep',
        description: 'Search for text patterns across files with optional extension filter.',
        inputSchema: {
            type: 'object',
            properties: {
                directory: { type: 'string' },
                query: { type: 'string' },
                extensions: { type: 'string', description: 'Comma-separated extensions (e.g. js,py,ts)' }
            },
            required: ['directory', 'query']
        }
    },
    {
        name: 'gravity_file_info',
        description: 'Get detailed file info (size, permissions, timestamps).',
        inputSchema: {
            type: 'object',
            properties: { path: { type: 'string' } },
            required: ['path']
        }
    },
    {
        name: 'gravity_outline',
        description: 'Get file structure/outline (functions, classes, exports).',
        inputSchema: {
            type: 'object',
            properties: { path: { type: 'string' } },
            required: ['path']
        }
    },
    {
        name: 'gravity_view_symbol',
        description: 'View a specific symbol (function/class) definition in a file.',
        inputSchema: {
            type: 'object',
            properties: {
                path: { type: 'string' },
                symbol: { type: 'string' }
            },
            required: ['path', 'symbol']
        }
    },
    {
        name: 'gravity_diff',
        description: 'Compare two files and show differences.',
        inputSchema: {
            type: 'object',
            properties: {
                file_a: { type: 'string' },
                file_b: { type: 'string' }
            },
            required: ['file_a', 'file_b']
        }
    },
    // ── Web / Network ────────────────────────────────────────
    {
        name: 'gravity_fetch_url',
        description: 'Fetch contents of a URL (HTTP GET).',
        inputSchema: {
            type: 'object',
            properties: { url: { type: 'string' } },
            required: ['url']
        }
    },
    {
        name: 'gravity_web_search',
        description: 'Search the web for a query via backend.',
        inputSchema: {
            type: 'object',
            properties: { query: { type: 'string' } },
            required: ['query']
        }
    },
    {
        name: 'gravity_download_file',
        description: 'Download a file from a URL to a local path.',
        inputSchema: {
            type: 'object',
            properties: {
                url: { type: 'string' },
                dest: { type: 'string' }
            },
            required: ['url', 'dest']
        }
    },
    // ── Package Management ───────────────────────────────────
    {
        name: 'gravity_install_package',
        description: 'Install a package via npm, pip, or apt.',
        inputSchema: {
            type: 'object',
            properties: {
                manager: { type: 'string', description: 'npm, pip, or apt' },
                package: { type: 'string' }
            },
            required: ['manager', 'package']
        }
    },
    // ── IDE UI ───────────────────────────────────────────────
    {
        name: 'gravity_open_terminal',
        description: 'Open a new terminal in the IDE bottom panel, optionally with a command.',
        inputSchema: {
            type: 'object',
            properties: { command: { type: 'string' } }
        }
    },
    // ── Sovereign Modules ────────────────────────────────────
    {
        name: 'gravity_run_sovereign_module',
        description: 'Execute a native Sovereign Python module via the Omega backend API.',
        inputSchema: {
            type: 'object',
            properties: {
                module_id: { type: 'string' },
                params: { type: 'object', default: {} }
            },
            required: ['module_id']
        }
    },
    // ── Health ───────────────────────────────────────────────
    {
        name: 'gravity_health',
        description: 'Server health check with uptime and tool count.',
        inputSchema: { type: 'object', properties: {} }
    },
];

// ── Foundation Utilities ─────────────────────────────────────────────────
function _sendToRenderer(channel, ...args) {
    try {
        const win = _ctx.getWindow();
        if (win && win.webContents && !win.webContents.isDestroyed()) {
            win.webContents.send(channel, ...args);
            return true;
        }
    } catch { /* window may be destroyed between check and send */ }
    return false;
}

function _text(t) { return { content: [{ type: 'text', text: String(t) }] }; }

/** Validate that a path argument is absolute and not obviously dangerous */
function _validatePath(p, label = 'path') {
    if (typeof p !== 'string' || p.trim().length === 0) {
        throw new Error(`${label} is required and must be a non-empty string`);
    }
    // Normalize and reject relative traversal
    const resolved = path.resolve(p);
    // Block known system-critical dirs
    const blocked = process.platform === 'win32'
        ? ['C:\\Windows\\System32', 'C:\\Windows\\SysWOW64', 'C:\\$Recycle.Bin']
        : ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/boot', '/dev', '/proc', '/sys'];
    for (const b of blocked) {
        if (resolved.toLowerCase().startsWith(b.toLowerCase())) {
            throw new Error(`Blocked: path targets protected system directory: ${b}`);
        }
    }
    return resolved;
}

/** Validate required string argument */
function _requireStr(args, key) {
    if (typeof args[key] !== 'string' || args[key].trim().length === 0) {
        throw new Error(`Missing required argument: ${key}`);
    }
    return args[key];
}

const handlers = {
    // ── FILE OPS ─────────────────────────────────────────────
    async gravity_read_file(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        if (!fs.existsSync(p)) throw new Error(`File not found: ${p}`);
        const content = fs.readFileSync(p, 'utf8');
        const lines = content.split('\n');
        const offset = (args.offset || 1) - 1;
        const limit = args.limit || 500;
        const sliced = lines.slice(offset, offset + limit);
        return { content: [{ type: 'text', text: sliced.join('\n') }], metadata: { totalLines: lines.length } };
    },

    async gravity_write_file(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        _requireStr(args, 'content');
        const dir = path.dirname(p);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(p, args.content, 'utf8');
        _sendToRenderer('omega:open-file', p);
        return _text(`Written ${args.content.length} bytes to ${p}`);
    },

    async gravity_patch_file(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        _requireStr(args, 'old_string');
        if (typeof args.new_string !== 'string') throw new Error('Missing required argument: new_string');
        if (!fs.existsSync(p)) throw new Error(`File not found: ${p}`);
        let content = fs.readFileSync(p, 'utf8');
        const idx = content.indexOf(args.old_string);
        if (idx === -1) throw new Error(`old_string not found in ${p}`);
        content = content.substring(0, idx) + args.new_string + content.substring(idx + args.old_string.length);
        fs.writeFileSync(p, content, 'utf8');
        _sendToRenderer('omega:open-file', p);
        return _text(`Patched ${p}`);
    },

    async gravity_list_dir(args) {
        const dir = args.path || '.';
        if (!fs.existsSync(dir)) throw new Error(`Not found: ${dir}`);
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        const lines = entries.map(e => {
            const full = path.join(dir, e.name);
            const size = e.isFile() ? (() => { try { return fs.statSync(full).size; } catch { return 0; } })() : '-';
            return `${e.isDirectory() ? 'd' : 'f'}  ${size}  ${e.name}`;
        });
        return _text(lines.join('\n'));
    },

    async gravity_file_exists(args) {
        return _text(JSON.stringify({ exists: fs.existsSync(args.path) }));
    },

    async gravity_mkdir(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        fs.mkdirSync(p, { recursive: true });
        return _text(`Created: ${p}`);
    },

    async gravity_delete(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        if (!fs.existsSync(p)) throw new Error(`Not found: ${p}`);
        if (args.recursive) fs.rmSync(p, { recursive: true, force: true });
        else fs.unlinkSync(p);
        return _text(`Deleted: ${p}`);
    },

    async gravity_rename(args) {
        const oldP = _validatePath(_requireStr(args, 'old_path'), 'old_path');
        const newP = _validatePath(_requireStr(args, 'new_path'), 'new_path');
        if (!fs.existsSync(oldP)) throw new Error(`Not found: ${oldP}`);
        fs.renameSync(oldP, newP);
        return _text(`Renamed ${oldP} → ${newP}`);
    },

    async gravity_open_in_editor(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        if (!fs.existsSync(p)) throw new Error(`File not found: ${p}`);
        const sent = _sendToRenderer('omega:open-file', p);
        return _text(sent ? `Opened in Monaco: ${p}` : 'No renderer window available');
    },

    // ── TERMINAL (with output capture, resource-capped) ─────
    async gravity_terminal_create() {
        if (!_ctx.ptyModule) throw new Error('node-pty not available');
        if (_ctx.terminals && _ctx.terminals.size >= MAX_TERMINALS) {
            throw new Error(`Terminal limit reached (${MAX_TERMINALS}). Kill an existing terminal first.`);
        }
        const id = `mcp-term-${++_ctx.terminalCounter.value}`;
        const shellPath = process.platform === 'win32' ? 'powershell.exe' : (process.env.SHELL || '/bin/bash');
        const pty = _ctx.ptyModule.spawn(shellPath, [], {
            name: 'xterm-256color', cols: 120, rows: 30,
            cwd: os.homedir(),
            env: { ...process.env, TERM: 'xterm-256color' },
        });
        _ctx.terminals.set(id, pty);
        _termOutputBuffers.set(id, '');
        const win = _ctx.getWindow();
        pty.onData((data) => {
            // Buffer output for MCP retrieval + send to renderer
            const buf = (_termOutputBuffers.get(id) || '') + data;
            _termOutputBuffers.set(id, buf.length > 50000 ? buf.slice(-50000) : buf);
            win?.webContents?.send('terminal:data', id, data);
        });
        pty.onExit(({ exitCode }) => {
            win?.webContents?.send('terminal:exit', id, exitCode);
            pty.removeAllListeners();
            _ctx.terminals.delete(id);
            // Keep output buffer for a bit after exit
            setTimeout(() => _termOutputBuffers.delete(id), 30000);
        });
        return _text(JSON.stringify({ terminal_id: id, pid: pty.pid }));
    },

    async gravity_terminal_exec(args) {
        _requireStr(args, 'terminal_id');
        const pty = _ctx.terminals.get(args.terminal_id);
        if (!pty) throw new Error(`Terminal not found: ${args.terminal_id}`);
        _requireStr(args, 'command');
        // Clear output buffer before sending command
        _termOutputBuffers.set(args.terminal_id, '');
        pty.write(args.command + '\r');
        // Wait for output to settle (3s default, customizable, capped 30s)
        const waitMs = Math.min(Math.max(args.wait_ms || 3000, 100), 30000);
        await new Promise(r => setTimeout(r, waitMs));
        // Collect buffered output
        const output = (_termOutputBuffers.get(args.terminal_id) || '').trim();
        // Strip ANSI escape codes for clean text (CSI sequences + OSC sequences + other escape sequences)
        const clean = output
            .replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '')
            .replace(/\x1b\][^\x07]*\x07/g, '')
            .replace(/\x1b\[\?[0-9;]*[a-zA-Z]/g, '')
            .replace(/\x1b[()][AB012]/g, '')
            .replace(/\r/g, '');
        return _text(clean || `(no output after ${waitMs}ms)`);
    },

    async gravity_terminal_kill(args) {
        _requireStr(args, 'terminal_id');
        const pty = _ctx.terminals.get(args.terminal_id);
        if (!pty) throw new Error(`Terminal not found: ${args.terminal_id}`);
        try { pty.kill(); } catch {}
        _ctx.terminals.delete(args.terminal_id);
        _termOutputBuffers.delete(args.terminal_id);
        return _text(`Killed: ${args.terminal_id}`);
    },

    // ── BROWSER ──────────────────────────────────────────────
    async gravity_browser_navigate(args) {
        if (!_ctx.browser) throw new Error('Browser module not available');
        _requireStr(args, 'url');
        const result = await _ctx.browser.navigate(args.url);
        return _text(JSON.stringify(result));
    },

    async gravity_browser_screenshot(args) {
        if (!_ctx.browser) throw new Error('Browser module not available');
        const result = await _ctx.browser.screenshot(args.name || 'screenshot');
        return _text(JSON.stringify(result));
    },

    async gravity_browser_close() {
        if (_ctx.browser) await _ctx.browser.close();
        return _text('Browser closed');
    },

    async gravity_browser_task(args) {
        if (!_ctx.browser) throw new Error('Browser module not available');
        const results = [];
        for (const step of (args.steps || [])) {
            try {
                switch (step.action) {
                    case 'navigate': results.push(await _ctx.browser.navigate(step.url)); break;
                    case 'click': results.push(await _ctx.browser.click(step.selector)); break;
                    case 'type': results.push(await _ctx.browser.type(step.selector, step.text)); break;
                    case 'screenshot': results.push(await _ctx.browser.screenshot(step.name || 'step')); break;
                    case 'extract': results.push(await _ctx.browser.extract(step.selector)); break;
                    default: results.push({ error: `Unknown action: ${step.action}` });
                }
            } catch (e) { results.push({ action: step.action, error: e.message }); }
        }
        return _text(JSON.stringify({ steps_completed: results.length, results }));
    },

    // ── CWD ──────────────────────────────────────────────────
    async gravity_cwd(args) {
        if (args.path) {
            const p = _validatePath(args.path);
            const stat = fs.statSync(p);
            if (!stat.isDirectory()) throw new Error(`Not a directory: ${p}`);
            _shellCwd = p;
        }
        return _text(JSON.stringify({ cwd: _shellCwd || os.homedir() }));
    },

    // ── SHELL (stateful — persistent cwd across calls) ────────
    async gravity_execute_command(args) {
        _requireStr(args, 'command');
        const timeoutMs = Math.min((args.timeout || 60) * 1000, 300000); // cap 5 min
        const cwd = args.cwd || _shellCwd || os.homedir();
        if (args.cwd && !fs.existsSync(args.cwd)) throw new Error(`cwd not found: ${args.cwd}`);

        return new Promise((resolve, reject) => {
            const marker = `__MCP_DONE_${Date.now()}_${Math.random().toString(36).slice(2)}__`;
            const fullCmd = process.platform === 'win32'
                ? `${args.command}; echo ''; echo '${marker}'; (Get-Location).Path`
                : `${args.command}; echo ''; echo '${marker}'; pwd`;

            const opts = {
                timeout: timeoutMs,
                maxBuffer: 10 * 1024 * 1024,
                cwd,
                shell: process.platform === 'win32' ? 'powershell.exe' : true,
            };

            exec(fullCmd, opts, (error, stdout, stderr) => {
                if (error && error.killed) {
                    resolve(_text(`TIMEOUT after ${args.timeout || 60}s:\n${stdout}\n${stderr}`));
                    return;
                }
                // Parse marker to extract output and new cwd
                let output = stdout;
                const markerIdx = stdout.indexOf(marker);
                if (markerIdx !== -1) {
                    output = stdout.substring(0, markerIdx).trim();
                    const afterMarker = stdout.substring(markerIdx + marker.length).trim();
                    if (afterMarker) _shellCwd = afterMarker.split('\n')[0].trim();
                }
                const result = output + (stderr ? `\n---STDERR---\n${stderr}` : '');
                resolve(_text(result));
            });
        });
    },

    // ── SYSTEM ───────────────────────────────────────────────
    async gravity_hardware_info() {
        const cpus = os.cpus();
        const info = {
            cpu: { model: cpus[0]?.model, cores: cpus.length },
            memory: {
                total_gb: (os.totalmem() / 1e9).toFixed(1),
                free_gb: (os.freemem() / 1e9).toFixed(1),
                used_pct: ((os.totalmem() - os.freemem()) / os.totalmem() * 100).toFixed(1),
            },
            platform: os.platform(), arch: os.arch(), uptime_h: (os.uptime() / 3600).toFixed(1),
        };
        try {
            const { execSync } = require('child_process');
            const nv = execSync('nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits', { timeout: 3000, encoding: 'utf8' });
            const p = nv.trim().split(',').map(s => s.trim());
            if (p.length >= 4) info.gpu = { name: p[0], vram_total_mb: +p[1], vram_used_mb: +p[2], util_pct: +p[3] };
        } catch {}
        return _text(JSON.stringify(info, null, 2));
    },

    // ── AGENT ────────────────────────────────────────────────
    async gravity_agent_chat(args) {
        if (!_ctx.agent) throw new Error('Agent not available');
        _requireStr(args, 'message');
        const result = await _ctx.agent.processRequest(args.message, args.model || 'gemini');
        return _text(typeof result === 'string' ? result : JSON.stringify({ type: result.type, text: result.text || result.message, steps: result.steps }));
    },

    async gravity_agent_status() {
        if (!_ctx.agent) return _text('Agent not initialized');
        return _text(JSON.stringify(_ctx.agent.getStatus()));
    },

    // ── BACKEND ──────────────────────────────────────────────
    async gravity_backend_status() {
        if (!_ctx.bridge) return _text('Bridge not initialized');
        return _text(JSON.stringify(_ctx.bridge.getStatus()));
    },

    async gravity_backend_execute(args) {
        if (!_ctx.bridge) throw new Error('Bridge not connected');
        _requireStr(args, 'module_id');
        if (!/^[a-zA-Z0-9_.-]+$/.test(args.module_id)) throw new Error(`Invalid module_id format: ${args.module_id}`);
        const result = await _ctx.bridge.post(`/api/modules/${args.module_id}/execute`, args.args || {});
        return _text(JSON.stringify(result));
    },

    // ── CODE INTELLIGENCE ────────────────────────────────────
    async gravity_find_files(args) {
        _requireStr(args, 'pattern');
        _requireStr(args, 'directory');
        const results = [];
        let regex;
        try {
            regex = new RegExp(args.pattern.replace(/\*/g, '.*').replace(/\?/g, '.'), 'i');
        } catch {
            throw new Error(`Invalid pattern: ${args.pattern}`);
        }
        function walk(dir, depth) {
            if (depth > 8 || results.length >= 200) return;
            try {
                const entries = fs.readdirSync(dir, { withFileTypes: true });
                for (const e of entries) {
                    if (e.name.startsWith('.') || e.name === 'node_modules' || e.name === '__pycache__') continue;
                    const full = path.join(dir, e.name);
                    if (e.isDirectory()) { walk(full, depth + 1); continue; }
                    if (regex.test(e.name)) results.push(full);
                }
            } catch {}
        }
        walk(args.directory, 0);
        return _text(JSON.stringify({ pattern: args.pattern, matches: results, count: results.length }));
    },

    async gravity_grep(args) {
        _requireStr(args, 'query');
        _requireStr(args, 'directory');
        const results = [];
        const extFilter = args.extensions ? new Set(args.extensions.split(',').map(e => '.' + e.trim().replace(/^\./, ''))) : null;
        function walk(dir, depth) {
            if (depth > 8 || results.length >= 100) return;
            try {
                const entries = fs.readdirSync(dir, { withFileTypes: true });
                for (const e of entries) {
                    if (e.name.startsWith('.') || e.name === 'node_modules' || e.name === '__pycache__') continue;
                    const full = path.join(dir, e.name);
                    if (e.isDirectory()) { walk(full, depth + 1); continue; }
                    if (extFilter && !extFilter.has(path.extname(e.name).toLowerCase())) continue;
                    try {
                        const content = fs.readFileSync(full, 'utf8');
                        const lines = content.split('\n');
                        for (let i = 0; i < lines.length && results.length < 100; i++) {
                            if (lines[i].includes(args.query)) {
                                results.push({ file: full, line: i + 1, text: lines[i].trim().substring(0, 200) });
                            }
                        }
                    } catch {}
                }
            } catch {}
        }
        walk(args.directory, 0);
        return _text(JSON.stringify({ query: args.query, matches: results, count: results.length }));
    },

    async gravity_file_info(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        if (!fs.existsSync(p)) throw new Error(`File not found: ${p}`);
        const stat = fs.statSync(p);
        return _text(JSON.stringify({
            path: p, size: stat.size, isDirectory: stat.isDirectory(),
            created: stat.birthtime.toISOString(), modified: stat.mtime.toISOString(),
            mode: '0' + (stat.mode & parseInt('777', 8)).toString(8),
        }));
    },

    async gravity_outline(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        if (!fs.existsSync(p)) throw new Error(`File not found: ${p}`);
        const content = fs.readFileSync(p, 'utf8');
        const ext = path.extname(p).toLowerCase();
        const symbols = [];
        const patterns = ['.js','.ts','.jsx','.tsx'].includes(ext)
            ? [/(?:export\s+)?(?:async\s+)?function\s+(\w+)/g, /(?:export\s+)?class\s+(\w+)/g, /(?:const|let|var)\s+(\w+)\s*=/g]
            : ext === '.py' ? [/^(?:async\s+)?def\s+(\w+)/gm, /^class\s+(\w+)/gm] : [];
        for (const pat of patterns) {
            let m; while ((m = pat.exec(content)) !== null) {
                symbols.push({ name: m[1], line: content.substring(0, m.index).split('\n').length });
            }
        }
        return _text(JSON.stringify({ path: args.path, symbols, count: symbols.length }));
    },

    async gravity_view_symbol(args) {
        const p = _validatePath(_requireStr(args, 'path'));
        _requireStr(args, 'symbol');
        if (!fs.existsSync(p)) throw new Error(`File not found: ${p}`);
        const content = fs.readFileSync(p, 'utf8');
        const lines = content.split('\n');
        // Escape symbol for safe regex use
        const escaped = args.symbol.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(function|class|def|const|let|var)\\s+${escaped}\\b`);
        for (let i = 0; i < lines.length; i++) {
            if (regex.test(lines[i])) {
                return _text(lines.slice(i, Math.min(i + 50, lines.length)).join('\n'));
            }
        }
        throw new Error(`Symbol '${args.symbol}' not found in ${p}`);
    },

    async gravity_diff(args) {
        const fileA = _validatePath(_requireStr(args, 'file_a'), 'file_a');
        const fileB = _validatePath(_requireStr(args, 'file_b'), 'file_b');
        if (!fs.existsSync(fileA)) throw new Error(`File not found: ${fileA}`);
        if (!fs.existsSync(fileB)) throw new Error(`File not found: ${fileB}`);
        const { execSync } = require('child_process');
        try {
            const out = execSync(`diff -u "${fileA.replace(/"/g, '')}" "${fileB.replace(/"/g, '')}"`, { encoding: 'utf8', timeout: 5000 });
            return _text(out || 'Files are identical');
        } catch (e) { return _text(e.stdout || e.message); }
    },

    // ── WEB / NETWORK ────────────────────────────────────────
    async gravity_fetch_url(args) {
        _requireStr(args, 'url');
        if (!/^https?:\/\//i.test(args.url)) throw new Error('URL must start with http:// or https://');
        const protocol = args.url.startsWith('https') ? require('https') : require('http');
        const MAX_RESPONSE = 500000; // 500KB cap
        return new Promise((resolve, reject) => {
            const req = protocol.get(args.url, { timeout: 15000 }, (res) => {
                // Follow redirects (up to 5)
                if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location) {
                    const redirectCount = (args._redirects || 0) + 1;
                    if (redirectCount > 5) { resolve(_text(JSON.stringify({ error: 'Too many redirects' }))); return; }
                    resolve(handlers.gravity_fetch_url({ url: res.headers.location, _redirects: redirectCount }));
                    return;
                }
                let data = '';
                res.on('data', c => {
                    data += c;
                    if (data.length > MAX_RESPONSE) { res.destroy(); data = data.substring(0, MAX_RESPONSE); }
                });
                res.on('end', () => resolve(_text(JSON.stringify({ url: args.url, status: res.statusCode, content: data.substring(0, 15000), bytes: data.length }))));
            });
            req.on('error', e => resolve(_text(JSON.stringify({ url: args.url, error: e.message }))));
            req.on('timeout', () => { req.destroy(); resolve(_text(JSON.stringify({ url: args.url, error: 'Request timeout (15s)' }))); });
        });
    },

    async gravity_web_search(args) {
        _requireStr(args, 'query');
        if (_ctx.bridge) {
            try {
                const result = await _ctx.bridge.post('/api/search/web', { query: args.query });
                return _text(JSON.stringify(result));
            } catch {}
        }
        return _text(JSON.stringify({ query: args.query, results: [], note: 'Web search requires backend' }));
    },

    async gravity_download_file(args) {
        _requireStr(args, 'url');
        if (!/^https?:\/\//i.test(args.url)) throw new Error('URL must start with http:// or https://');
        const dest = _validatePath(_requireStr(args, 'dest'));
        const protocol = args.url.startsWith('https') ? require('https') : require('http');
        const dir = path.dirname(dest);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        const MAX_DOWNLOAD = 100 * 1024 * 1024; // 100MB cap
        return new Promise((resolve, reject) => {
            const req = protocol.get(args.url, { timeout: 60000 }, (res) => {
                // Follow redirects
                if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location) {
                    resolve(handlers.gravity_download_file({ url: res.headers.location, dest: args.dest, _redirects: (args._redirects || 0) + 1 }));
                    return;
                }
                if ((args._redirects || 0) > 5) { resolve(_text(JSON.stringify({ error: 'Too many redirects' }))); return; }
                if (res.statusCode >= 400) { resolve(_text(JSON.stringify({ url: args.url, error: `HTTP ${res.statusCode}` }))); return; }
                let bytes = 0;
                const file = fs.createWriteStream(dest);
                res.on('data', chunk => {
                    bytes += chunk.length;
                    if (bytes > MAX_DOWNLOAD) { res.destroy(); file.close(); fs.unlink(dest, () => {}); }
                });
                res.pipe(file);
                file.on('finish', () => { file.close(); resolve(_text(JSON.stringify({ url: args.url, dest, size: bytes, success: true }))); });
                file.on('error', (e) => { fs.unlink(dest, () => {}); resolve(_text(JSON.stringify({ url: args.url, error: e.message }))); });
            });
            req.on('error', (e) => { fs.unlink(dest, () => {}); resolve(_text(JSON.stringify({ url: args.url, error: e.message }))); });
            req.on('timeout', () => { req.destroy(); resolve(_text(JSON.stringify({ url: args.url, error: 'Download timeout (60s)' }))); });
        });
    },

    // ── PACKAGE MANAGEMENT ───────────────────────────────────
    async gravity_install_package(args) {
        const manager = _requireStr(args, 'manager');
        const pkg = _requireStr(args, 'package');
        // Sanitize package name — only allow alphanumeric, hyphens, underscores, dots, slashes, @
        if (!/^[@a-zA-Z0-9_.\/-]+$/.test(pkg)) throw new Error(`Invalid package name: ${pkg}`);
        const cmds = { npm: `npm install ${pkg}`, pip: `pip install ${pkg}`, apt: `sudo apt-get install -y ${pkg}` };
        const cmd = cmds[manager];
        if (!cmd) throw new Error(`Unknown package manager: ${manager}. Use: npm, pip, apt`);
        return handlers.gravity_execute_command({ command: cmd, timeout: manager === 'pip' ? 300 : 180 });
    },

    // ── IDE UI ───────────────────────────────────────────────
    async gravity_open_terminal(args) {
        const sent = _sendToRenderer('agent:open-terminal', { command: args.command || null });
        return _text(sent ? `Opened terminal${args.command ? ': ' + args.command : ''}` : 'No renderer window');
    },

    // ── SOVEREIGN MODULES ────────────────────────────────────
    async gravity_run_sovereign_module(args) {
        if (!_ctx.bridge) throw new Error('Backend bridge not connected');
        _requireStr(args, 'module_id');
        if (!/^[a-zA-Z0-9_.-]+$/.test(args.module_id)) throw new Error(`Invalid module_id format: ${args.module_id}`);
        const result = await _ctx.bridge.post(`/api/modules/${args.module_id}/run`, args.params || {});
        return _text(JSON.stringify(result));
    },

    // ── UPLOAD / IMAGE / VERITAS ─────────────────────────────
    async gravity_upload_file(args) {
        const source = _validatePath(_requireStr(args, 'source'), 'source');
        const dest = _validatePath(_requireStr(args, 'dest'), 'dest');
        if (!fs.existsSync(source)) throw new Error(`Source not found: ${source}`);
        const destDir = path.dirname(dest);
        if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
        fs.copyFileSync(source, dest);
        const stat = fs.statSync(dest);
        return _text(JSON.stringify({ source, dest, size: stat.size, success: true }));
    },

    async gravity_generate_image(args) {
        if (_ctx.bridge) {
            try {
                const result = await _ctx.bridge.post('/api/image/generate', {
                    prompt: args.prompt, output_path: args.output_path,
                    width: args.width || 512, height: args.height || 512,
                });
                return _text(JSON.stringify(result));
            } catch (e) { throw new Error(`Image generation failed: ${e.message}`); }
        }
        throw new Error('Image generation requires backend bridge');
    },

    async gravity_assess_file(args) {
        if (!fs.existsSync(args.path)) throw new Error(`File not found: ${args.path}`);
        if (_ctx.bridge) {
            try {
                const result = await _ctx.bridge.post('/api/veritas/assess', {
                    path: args.path, mode: args.mode || 'veritas',
                });
                return _text(JSON.stringify(result));
            } catch (e) { throw new Error(`VERITAS assessment failed: ${e.message}`); }
        }
        // Fallback: basic static analysis if no backend
        const content = fs.readFileSync(args.path, 'utf8');
        const lines = content.split('\n').length;
        const ext = path.extname(args.path);
        return _text(JSON.stringify({
            path: args.path, mode: 'offline', lines, ext,
            note: 'Full VERITAS pipeline requires backend connection'
        }));
    },

    // ── HEALTH ───────────────────────────────────────────────
    async gravity_health() {
        return _text(JSON.stringify({
            status: 'operational',
            server: SERVER_NAME,
            version: SERVER_VERSION,
            uptime_s: Math.floor(process.uptime()),
            tools: TOOLS.length,
            sessions: sessions.size,
            window: !!_ctx.getWindow(),
            terminals: _ctx.terminals ? _ctx.terminals.size : 0,
        }));
    },
};

// ── JSON-RPC Router (validated) ──────────────────────────────────────────
async function handleMessage(msg) {
    // Structural validation
    if (!msg || typeof msg !== 'object') {
        return { jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error: expected JSON object' } };
    }
    if (msg.jsonrpc && msg.jsonrpc !== '2.0') {
        return { jsonrpc: '2.0', id: msg.id || null, error: { code: -32600, message: 'Invalid JSON-RPC version' } };
    }

    const { id, method, params } = msg;

    if (typeof method !== 'string') {
        return { jsonrpc: '2.0', id: id || null, error: { code: -32600, message: 'Invalid request: method must be a string' } };
    }

    switch (method) {
        case 'initialize':
            return { jsonrpc: '2.0', id, result: {
                protocolVersion: PROTOCOL_VERSION,
                capabilities: { tools: { listChanged: false } },
                serverInfo: { name: SERVER_NAME, version: SERVER_VERSION }
            }};

        case 'notifications/initialized':
            return null;  // notification — no response

        case 'tools/list':
            return { jsonrpc: '2.0', id, result: { tools: TOOLS } };

        case 'tools/call': {
            const name = params?.name;
            if (typeof name !== 'string') {
                return { jsonrpc: '2.0', id, error: { code: -32602, message: 'Invalid params: name is required' } };
            }
            const args = params?.arguments || {};
            const handler = handlers[name];
            if (!handler) {
                return { jsonrpc: '2.0', id, error: { code: -32601, message: `Unknown tool: ${name}` } };
            }

            try {
                const result = await handler(args);
                // Validate handler returned proper content shape
                if (!result || !Array.isArray(result.content)) {
                    console.error(`[MCP] Tool ${name} returned invalid shape:`, typeof result);
                    return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: '(tool returned no content)' }], isError: true } };
                }
                return { jsonrpc: '2.0', id, result: { content: result.content, isError: false } };
            } catch (err) {
                const stack = err.stack ? err.stack.split('\n').slice(0, 3).join('\n') : '';
                console.error(`[MCP] Tool ${name} error: ${err.message}\n${stack}`);
                return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: `Error: ${err.message}` }], isError: true } };
            }
        }

        default:
            // Notifications (no id) don't get error responses
            if (id == null) return null;
            return { jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } };
    }
}

// ── HTTP Server (hardened) ───────────────────────────────────────────────
let _server = null;

function startServer(ctx) {
    // Inject context references
    if (ctx) {
        _ctx.getWindow = ctx.getWindow || (() => ctx.mainWindow);
        _ctx.terminals = ctx.terminals || new Map();
        _ctx.browser = ctx.browser || null;
        _ctx.bridge = ctx.bridge || null;
        _ctx.agent = ctx.agent || null;
        _ctx.ptyModule = ctx.ptyModule || null;
        _ctx.terminalCounter = ctx.terminalCounter || _ctx.terminalCounter;
    }

    _server = http.createServer((req, res) => {
        // CORS headers
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

        if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

        let url;
        try {
            url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
        } catch {
            res.writeHead(400); res.end('Bad Request'); return;
        }

        // ── SSE endpoint ─────────────────────────────────────────
        if (url.pathname === '/sse' && req.method === 'GET') {
            if (sessions.size >= MAX_SESSIONS) {
                console.warn(`[MCP] Session limit reached (${MAX_SESSIONS}), rejecting`);
                res.writeHead(503); res.end('Too many sessions'); return;
            }
            const transport = new SseTransport(req, res);
            sessions.set(transport.sessionId, transport);
            console.log(`[MCP] Client connected: ${transport.sessionId} (${sessions.size}/${MAX_SESSIONS})`);
            transport.on('close', () => {
                sessions.delete(transport.sessionId);
                console.log(`[MCP] Client disconnected: ${transport.sessionId} (${sessions.size}/${MAX_SESSIONS})`);
            });
            return;
        }

        // ── Message endpoint ─────────────────────────────────────
        if (url.pathname === '/messages' && req.method === 'POST') {
            const sessionId = url.searchParams.get('session_id');
            const transport = sessions.get(sessionId);
            if (!transport) { res.writeHead(404); res.end('Session not found'); return; }
            if (transport.closed) { sessions.delete(sessionId); res.writeHead(410); res.end('Session closed'); return; }

            let body = '';
            let aborted = false;

            req.on('data', chunk => {
                body += chunk;
                if (body.length > MAX_BODY_BYTES) {
                    aborted = true;
                    req.destroy();
                    if (!res.headersSent) { res.writeHead(413); res.end('Request body too large'); }
                }
            });

            req.on('error', () => {
                if (!res.headersSent) { res.writeHead(400); res.end('Request error'); }
            });

            req.on('end', async () => {
                if (aborted) return;
                try {
                    const msg = JSON.parse(body);
                    const response = await handleMessage(msg);
                    transport.sendMessage(response);
                    if (!res.headersSent) { res.writeHead(202); res.end('Accepted'); }
                } catch (err) {
                    console.error('[MCP] Message processing error:', err.message);
                    if (!res.headersSent) {
                        res.writeHead(400);
                        res.end(JSON.stringify({ jsonrpc: '2.0', error: { code: -32700, message: 'Parse error' } }));
                    }
                }
            });
            return;
        }

        // ── Health endpoint ──────────────────────────────────────
        if (url.pathname === '/health' && req.method === 'GET') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                status: 'ok',
                version: SERVER_VERSION,
                tools: TOOLS.length,
                sessions: sessions.size,
                max_sessions: MAX_SESSIONS,
                terminals: _ctx.terminals ? _ctx.terminals.size : 0,
                max_terminals: MAX_TERMINALS,
                uptime_s: Math.floor(process.uptime()),
            }));
            return;
        }

        res.writeHead(404); res.end('Not Found');
    });

    _server.on('error', (err) => {
        console.error(`[MCP] Server error: ${err.message}`);
    });

    _server.listen(SSE_PORT, () => {
        console.log(`[MCP] ═══════════════════════════════════════════════`);
        console.log(`[MCP] Gravity Omega MCP Server v${SERVER_VERSION}`);
        console.log(`[MCP] SSE:    http://localhost:${SSE_PORT}/sse`);
        console.log(`[MCP] Health: http://localhost:${SSE_PORT}/health`);
        console.log(`[MCP] Tools:  ${TOOLS.length} IDE capabilities exposed`);
        console.log(`[MCP] Limits: ${MAX_SESSIONS} sessions, ${MAX_TERMINALS} terminals, ${(MAX_BODY_BYTES / 1e6).toFixed(0)}MB body`);
        console.log(`[MCP] ═══════════════════════════════════════════════`);
    });

    return _server;
}

// ── Graceful Shutdown ────────────────────────────────────────────────────
function shutdown() {
    console.log('[MCP] Shutting down...');

    // 1. Close all SSE sessions (stops heartbeats + max-age timers)
    for (const [id, transport] of sessions) {
        transport.close();
        sessions.delete(id);
    }

    // 2. Kill all MCP-spawned terminals
    if (_ctx.terminals) {
        for (const [id, pty] of _ctx.terminals) {
            try { pty.kill(); } catch {}
            _ctx.terminals.delete(id);
        }
    }
    _termOutputBuffers.clear();

    // 3. Close HTTP server
    if (_server) {
        _server.close(() => console.log('[MCP] Server closed'));
        _server = null;
    }

    console.log('[MCP] Shutdown complete');
}

// Process-level cleanup (when running standalone)
if (require.main === module) {
    process.on('SIGTERM', () => { shutdown(); process.exit(0); });
    process.on('SIGINT', () => { shutdown(); process.exit(0); });
    startServer();
}

module.exports = { startServer, shutdown, TOOLS };


