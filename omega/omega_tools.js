/**
 * OMEGA TOOLS v4.1 — Tool Registry + Executor
 *
 * 24 typed tools with three safety tiers:
 *   SAFE (12)      — Auto-execute, no approval
 *   GATED (9)      — Auto for non-destructive, approval for destructive
 *   RESTRICTED (3) — Always requires approval
 *
 * The ToolExecutor handles actual execution, delegating to
 * Node.js fs/child_process or the Python backend via bridge.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync, spawn } = require('child_process');
const crypto = require('crypto');

const SAFETY = { SAFE: 'SAFE', GATED: 'GATED', RESTRICTED: 'RESTRICTED' };

// ══════════════════════════════════════════════════════════════
// TOOL REGISTRY — 24 tools
// ══════════════════════════════════════════════════════════════

const TOOL_REGISTRY = {
    // ── SAFE (12) — Auto-execute ─────────────────────────────
    readFile: {
        safety: SAFETY.SAFE,
        description: 'Read a file and return its contents',
        args: { path: { type: 'string', required: true } },
    },
    listDir: {
        safety: SAFETY.SAFE,
        description: 'List directory contents with file types and sizes',
        args: { path: { type: 'string', required: true }, recursive: { type: 'boolean' } },
    },
    findFiles: {
        safety: SAFETY.SAFE,
        description: 'Find files matching a glob pattern',
        args: { directory: { type: 'string', required: true }, pattern: { type: 'string', required: true } },
    },
    grep: {
        safety: SAFETY.SAFE,
        description: 'Search for text patterns across files in a directory',
        args: { directory: { type: 'string', required: true }, query: { type: 'string', required: true }, extensions: { type: 'string' } },
    },
    outline: {
        safety: SAFETY.SAFE,
        description: 'Get the structure/outline of a file (functions, classes, exports)',
        args: { path: { type: 'string', required: true } },
    },
    viewSymbol: {
        safety: SAFETY.SAFE,
        description: 'View a specific symbol (function/class) definition in a file',
        args: { path: { type: 'string', required: true }, symbol: { type: 'string', required: true } },
    },
    fetchUrl: {
        safety: SAFETY.SAFE,
        description: 'Fetch the contents of a URL',
        args: { url: { type: 'string', required: true } },
    },
    webSearch: {
        safety: SAFETY.SAFE,
        description: 'Search the web for a query',
        args: { query: { type: 'string', required: true } },
    },
    hardware: {
        safety: SAFETY.SAFE,
        description: 'Get current hardware stats (CPU, RAM, disk, GPU)',
        args: {},
    },
    fileInfo: {
        safety: SAFETY.SAFE,
        description: 'Get detailed info about a file (size, permissions, timestamps)',
        args: { path: { type: 'string', required: true } },
    },
    diff: {
        safety: SAFETY.SAFE,
        description: 'Compare two files and show differences',
        args: { fileA: { type: 'string', required: true }, fileB: { type: 'string', required: true } },
    },
    cwd: {
        safety: SAFETY.SAFE,
        description: 'Get the current working directory',
        args: {},
    },
    openFile: {
        safety: SAFETY.SAFE,
        description: 'Open a file in the Gravity Omega editor (Monaco with tabs). Use this when the user asks to open, view, or edit a file.',
        args: { path: { type: 'string', required: true }, line: { type: 'number' } },
    },
    openTerminal: {
        safety: SAFETY.SAFE,
        description: 'Open a new terminal in the bottom panel of Gravity Omega. Use this when the user asks to open a terminal, shell, or command line.',
        args: { command: { type: 'string' } },
    },

    // ── GATED (9) — Auto for non-destructive ─────────────────
    writeFile: {
        safety: SAFETY.GATED,
        description: 'Write content to a file (creates parent directories)',
        args: { path: { type: 'string', required: true }, content: { type: 'string', required: true } },
    },
    editFile: {
        safety: SAFETY.GATED,
        description: 'Edit a file by replacing specific text (find and replace)',
        args: { path: { type: 'string', required: true }, find: { type: 'string', required: true }, replace: { type: 'string', required: true } },
    },
    exec: {
        safety: SAFETY.GATED,
        description: 'Execute a shell command and return stdout/stderr',
        args: { command: { type: 'string', required: true }, cwd: { type: 'string' }, timeout: { type: 'number' } },
    },
    browser: {
        safety: SAFETY.GATED,
        description: 'Navigate to a URL in an automated browser',
        args: { url: { type: 'string', required: true } },
    },
    download: {
        safety: SAFETY.GATED,
        description: 'Download a file from a URL to a local path',
        args: { url: { type: 'string', required: true }, dest: { type: 'string', required: true } },
    },
    upload: {
        safety: SAFETY.GATED,
        description: 'Upload a file to a destination (e.g., GitHub, server)',
        args: { source: { type: 'string', required: true }, dest: { type: 'string', required: true } },
    },
    generateImage: {
        safety: SAFETY.GATED,
        description: 'Generate an image using AI',
        args: { prompt: { type: 'string', required: true }, output: { type: 'string' } },
    },
    installPkg: {
        safety: SAFETY.GATED,
        description: 'Install a package via npm/pip/apt',
        args: { manager: { type: 'string', required: true }, package: { type: 'string', required: true } },
    },
    createDir: {
        safety: SAFETY.GATED,
        description: 'Create a directory (recursive)',
        args: { path: { type: 'string', required: true } },
    },
    runSovereignModule: {
        safety: SAFETY.GATED,
        description: 'Execute a native C:\\Veritas_Lab sovereign Python module via the Omega backend API',
        args: { moduleId: { type: 'string', required: true }, params: { type: 'object', description: 'JSON object containing arguments for the module' } },
    },

    // ── RESTRICTED (3) — Always requires approval ────────────
    deleteFile: {
        safety: SAFETY.RESTRICTED,
        description: 'Delete a file or directory',
        args: { path: { type: 'string', required: true }, recursive: { type: 'boolean' } },
    },
    reboot: {
        safety: SAFETY.RESTRICTED,
        description: 'Reboot the machine',
        args: {},
    },
    serviceCtrl: {
        safety: SAFETY.RESTRICTED,
        description: 'Start/stop/restart a system service',
        args: { service: { type: 'string', required: true }, action: { type: 'string', required: true } },
    },
};

// ══════════════════════════════════════════════════════════════
// TOOL EXECUTOR
// ══════════════════════════════════════════════════════════════

class ToolExecutor {
    constructor({ bridge }) {
        this.bridge = bridge;
    }

    async execute(toolName, args) {
        const handler = this['_exec_' + toolName];
        if (!handler) throw new Error(`No handler for tool: ${toolName}`);
        return handler.call(this, args);
    }

    // ── SAFE Tools ───────────────────────────────────────────

    async _exec_readFile({ path: p }) {
        const content = fs.readFileSync(p, 'utf-8');
        return { path: p, content, size: content.length, lines: content.split('\n').length };
    }

    async _exec_openFile({ path: p, line }) {
        // Sends IPC to renderer to open the file in the Monaco editor
        const { BrowserWindow } = require('electron');
        const windows = BrowserWindow.getAllWindows();
        if (windows.length > 0) {
            windows[0].webContents.send('agent:open-file', { path: p, line: line || 1 });
        }
        return { opened: true, path: p, line: line || 1, message: `Opened ${path.basename(p)} in the editor` };
    }

    async _exec_openTerminal({ command }) {
        const { BrowserWindow } = require('electron');
        const windows = BrowserWindow.getAllWindows();
        if (windows.length > 0) {
            windows[0].webContents.send('agent:open-terminal', { command: command || null });
        }
        return { opened: true, message: command ? `Opened terminal and running: ${command}` : 'Opened a new terminal' };
    }

    async _exec_listDir({ path: p, recursive }) {
        const entries = fs.readdirSync(p, { withFileTypes: true });
        const result = entries.map(e => {
            const full = path.join(p, e.name);
            const info = { name: e.name, path: full, isDirectory: e.isDirectory() };
            if (e.isFile()) {
                try { info.size = fs.statSync(full).size; } catch { }
            }
            return info;
        });
        result.sort((a, b) => {
            if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1;
            return a.name.localeCompare(b.name);
        });
        return { path: p, entries: result, count: result.length };
    }

    async _exec_findFiles({ directory, pattern }) {
        const results = [];
        const regex = new RegExp(pattern.replace(/\*/g, '.*').replace(/\?/g, '.'), 'i');
        function walk(dir, depth) {
            if (depth > 8 || results.length >= 100) return;
            try {
                const entries = fs.readdirSync(dir, { withFileTypes: true });
                for (const e of entries) {
                    if (e.name.startsWith('.') || e.name === 'node_modules') continue;
                    const full = path.join(dir, e.name);
                    if (e.isDirectory()) { walk(full, depth + 1); continue; }
                    if (regex.test(e.name)) results.push(full);
                }
            } catch { }
        }
        walk(directory, 0);
        return { pattern, matches: results, count: results.length };
    }

    async _exec_grep({ directory, query, extensions }) {
        const results = [];
        const extFilter = extensions ? new Set(extensions.split(',').map(e => '.' + e.trim())) : null;
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
                        const content = fs.readFileSync(full, 'utf-8');
                        const lines = content.split('\n');
                        for (let i = 0; i < lines.length; i++) {
                            if (lines[i].includes(query)) {
                                results.push({ file: full, line: i + 1, text: lines[i].trim().substring(0, 200) });
                                if (results.length >= 100) return;
                            }
                        }
                    } catch { }
                }
            } catch { }
        }
        walk(directory, 0);
        return { query, matches: results, count: results.length };
    }

    async _exec_outline({ path: p }) {
        const content = fs.readFileSync(p, 'utf-8');
        const ext = path.extname(p).toLowerCase();
        const symbols = [];

        if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) {
            const patterns = [
                /(?:export\s+)?(?:async\s+)?function\s+(\w+)/g,
                /(?:export\s+)?class\s+(\w+)/g,
                /(?:const|let|var)\s+(\w+)\s*=/g,
                /module\.exports\s*=\s*\{([^}]+)\}/g,
            ];
            for (const pat of patterns) {
                let m;
                while ((m = pat.exec(content)) !== null) {
                    symbols.push({ name: m[1], line: content.substring(0, m.index).split('\n').length });
                }
            }
        } else if (ext === '.py') {
            const patterns = [
                /^(?:async\s+)?def\s+(\w+)/gm,
                /^class\s+(\w+)/gm,
            ];
            for (const pat of patterns) {
                let m;
                while ((m = pat.exec(content)) !== null) {
                    symbols.push({ name: m[1], line: content.substring(0, m.index).split('\n').length });
                }
            }
        }

        return { path: p, symbols, count: symbols.length };
    }

    async _exec_viewSymbol({ path: p, symbol }) {
        const content = fs.readFileSync(p, 'utf-8');
        const lines = content.split('\n');
        const regex = new RegExp(`(function|class|def|const|let|var)\\s+${symbol}\\b`);
        for (let i = 0; i < lines.length; i++) {
            if (regex.test(lines[i])) {
                const start = i;
                const end = Math.min(i + 50, lines.length);
                return { path: p, symbol, startLine: start + 1, content: lines.slice(start, end).join('\n') };
            }
        }
        return { error: `Symbol '${symbol}' not found in ${p}` };
    }

    async _exec_fetchUrl({ url }) {
        const protocol = url.startsWith('https') ? require('https') : require('http');
        return new Promise((resolve, reject) => {
            protocol.get(url, { timeout: 10000 }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => resolve({ url, status: res.statusCode, content: data.substring(0, 10000) }));
            }).on('error', e => reject(e));
        });
    }

    async _exec_webSearch({ query }) {
        // Use bridge if available
        try {
            const result = await this.bridge?.post('/api/search/web', { query });
            return result;
        } catch { }
        return { query, results: [], note: 'Web search requires backend connection' };
    }

    async _exec_hardware() {
        const cpus = os.cpus();
        return {
            cpu: { model: cpus[0]?.model, cores: cpus.length, loadAvg: os.loadavg() },
            memory: {
                total_gb: (os.totalmem() / 1e9).toFixed(1),
                free_gb: (os.freemem() / 1e9).toFixed(1),
                percent: ((os.totalmem() - os.freemem()) / os.totalmem() * 100).toFixed(1),
            },
            platform: os.platform(), arch: os.arch(),
        };
    }

    async _exec_fileInfo({ path: p }) {
        const stat = fs.statSync(p);
        return {
            path: p, size: stat.size, isDirectory: stat.isDirectory(),
            created: stat.birthtime.toISOString(), modified: stat.mtime.toISOString(),
            mode: '0' + (stat.mode & parseInt('777', 8)).toString(8),
        };
    }

    async _exec_diff({ fileA, fileB }) {
        try {
            const out = execSync(`diff -u "${fileA}" "${fileB}"`, { encoding: 'utf-8', timeout: 5000 });
            return { diff: out || 'Files are identical' };
        } catch (e) {
            return { diff: e.stdout || e.message };
        }
    }

    async _exec_cwd() {
        return { cwd: process.cwd() };
    }

    // ── GATED Tools ──────────────────────────────────────────

    async _exec_writeFile({ path: p, content }) {
        const dir = path.dirname(p);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(p, content, 'utf-8');
        return { path: p, written: content.length, success: true };
    }

    async _exec_editFile({ path: p, find, replace }) {
        const content = fs.readFileSync(p, 'utf-8');
        if (!content.includes(find)) {
            return { error: `Target text not found in ${p}`, path: p };
        }
        const newContent = content.replace(find, replace);
        fs.writeFileSync(p, newContent, 'utf-8');
        return { path: p, success: true, replaced: true };
    }

    async _exec_exec({ command, cwd: execCwd, timeout }) {
        const t = timeout || 30000;
        try {
            const output = execSync(command, {
                cwd: execCwd || process.env.HOME || os.homedir(),
                encoding: 'utf-8', timeout: t,
                maxBuffer: 1024 * 1024 * 10,
            });
            return { command, stdout: output.substring(0, 5000), exitCode: 0 };
        } catch (e) {
            return {
                command,
                stdout: (e.stdout || '').substring(0, 5000),
                stderr: (e.stderr || '').substring(0, 2000),
                exitCode: e.status || 1,
            };
        }
    }

    async _exec_browser({ url }) {
        // Delegate to OmegaBrowser via bridge
        return { url, note: 'Browser automation delegated to OmegaBrowser module' };
    }

    async _exec_download({ url, dest }) {
        return new Promise((resolve, reject) => {
            const protocol = url.startsWith('https') ? require('https') : require('http');
            const dir = path.dirname(dest);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            const file = fs.createWriteStream(dest);
            protocol.get(url, (res) => {
                res.pipe(file);
                file.on('finish', () => { file.close(); resolve({ url, dest, success: true }); });
            }).on('error', (e) => {
                fs.unlink(dest, () => { });
                reject(e);
            });
        });
    }

    async _exec_upload({ source, dest }) {
        return { source, dest, note: 'Upload requires backend integration' };
    }

    async _exec_runSovereignModule({ moduleId, params }) {
        if (!this.bridge) return { error: 'Backend bridge not connected' };
        try {
            const result = await this.bridge.post(`/api/modules/${moduleId}/run`, params || {});
            return result;
        } catch (e) {
            return { error: `Sovereign module execution failed: ${e.message}` };
        }
    }

    async _exec_generateImage({ prompt, output }) {
        return { prompt, output, note: 'Image generation requires backend AI integration' };
    }

    async _exec_installPkg({ manager, package: pkg }) {
        const cmds = {
            npm: `npm install ${pkg}`, pip: `pip install ${pkg}`,
            apt: `sudo apt-get install -y ${pkg}`,
        };
        const cmd = cmds[manager];
        if (!cmd) return { error: `Unknown package manager: ${manager}` };
        return this._exec_exec({ command: cmd, timeout: 120000 });
    }

    async _exec_createDir({ path: p }) {
        fs.mkdirSync(p, { recursive: true });
        return { path: p, created: true };
    }

    // ── RESTRICTED Tools ─────────────────────────────────────

    async _exec_deleteFile({ path: p, recursive }) {
        if (recursive) fs.rmSync(p, { recursive: true, force: true });
        else fs.unlinkSync(p);
        return { path: p, deleted: true };
    }

    async _exec_reboot() {
        execSync(process.platform === 'win32' ? 'shutdown /r /t 10' : 'sudo reboot', { timeout: 5000 });
        return { rebooting: true };
    }

    async _exec_serviceCtrl({ service, action }) {
        const cmd = process.platform === 'win32'
            ? `net ${action} "${service}"`
            : `sudo systemctl ${action} ${service}`;
        return this._exec_exec({ command: cmd, timeout: 15000 });
    }
}

// ── Invariant checker ────────────────────────────────────────
function assertApproved(toolName, approvalRecord) {
    const tool = TOOL_REGISTRY[toolName];
    if (!tool) throw new Error(`INVARIANT VIOLATION: Unknown tool '${toolName}'`);
    if (tool.safety === SAFETY.RESTRICTED && !approvalRecord) {
        throw new Error(`INVARIANT VIOLATION: RESTRICTED tool '${toolName}' executed without approval`);
    }
}

module.exports = { TOOL_REGISTRY, SAFETY, ToolExecutor, assertApproved };
