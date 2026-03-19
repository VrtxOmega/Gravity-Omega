/**
 * GRAVITY OMEGA v3.0 — Electron Main Process
 * Ported from Windows → WSL Ubuntu
 *
 * Architecture:
 *   main.js → preload.js → renderer (app.js)
 *   main.js → OmegaBridge → Python web_server.py (port 5000)
 *   main.js → OmegaAgent → Agentic Loop (Gemini/Ollama)
 */
const { app, BrowserWindow, ipcMain, dialog, Menu, protocol, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn, execSync } = require('child_process');

// ── CRASH DIAGNOSTICS — write to file since stdout may not flush ──
const CRASH_LOG = path.join(os.tmpdir(), 'gravity_omega_crash.log');
function crashLog(msg) {
    try { fs.appendFileSync(CRASH_LOG, `[${new Date().toISOString()}] ${msg}\n`); } catch {}
}
// Clear previous log on fresh start
try { fs.writeFileSync(CRASH_LOG, `=== GRAVITY OMEGA STARTED ${new Date().toISOString()} ===\n`); } catch {}
crashLog(`PID=${process.pid} argv=${process.argv.join(' ')}`);

// ── Omega Modules ────────────────────────────────────────────
const { OmegaBridge } = require('./omega/omega_bridge');
const { OmegaIPC } = require('./omega/omega_ipc');
const { OmegaContext } = require('./omega/omega_context');
const { OmegaHooks } = require('./omega/omega_hooks');
const { OmegaAgent } = require('./omega/omega_agent');
const { OmegaBrowser } = require('./omega/omega_browser');

// ── Global Instances ─────────────────────────────────────────
const bridge = new OmegaBridge();
const ipc = new OmegaIPC(bridge);
const context = new OmegaContext();
const hooks = new OmegaHooks();
const agent = new OmegaAgent({ context, hooks, bridge });
const browser = new OmegaBrowser({ screenshotDir: path.join(__dirname, 'screenshots') });

let mainWindow = null;

// ── PTY Terminals (node-pty) ─────────────────────────────────
const terminals = new Map();
let terminalCounter = 0;
let ptyModule = null;
try { ptyModule = require('node-pty'); } catch { console.warn('[Omega] node-pty not available'); }

// ── File Watcher (chokidar) ──────────────────────────────────
let watcher = null;
let chokidar = null;
try { chokidar = require('chokidar'); } catch { console.warn('[Omega] chokidar not available'); }

// (GPU flags removed — native Windows Electron handles GPU properly)

// ══════════════════════════════════════════════════════════════
// WINDOW
// ══════════════════════════════════════════════════════════════

// Prevent multiple windows — focus existing if already running
try {
    const gotLock = app.requestSingleInstanceLock();
    crashLog(`Single instance lock: gotLock=${gotLock}`);
    if (!gotLock) {
        crashLog('EXITING: second instance detected, calling app.quit()');
        app.quit();
    } else {
        app.on('second-instance', () => {
            crashLog('second-instance event fired');
            if (mainWindow) {
                if (mainWindow.isMinimized()) mainWindow.restore();
                mainWindow.focus();
            }
        });
    }
} catch (e) {
    crashLog(`Single instance lock EXCEPTION: ${e.message}`);
    console.warn('[Omega] Single instance lock failed:', e.message);
}

// Catch EPIPE and other stream errors that crash Electron
process.on('uncaughtException', (err) => {
    crashLog(`UNCAUGHT EXCEPTION: ${err.code || ''} ${err.message} ${err.stack || ''}`);
    if (err.code === 'EPIPE' || err.code === 'ERR_STREAM_DESTROYED') {
        console.warn('[Omega] Caught stream error (non-fatal):', err.code);
        return; // swallow — pipe broke, not a real crash
    }
    console.error('[Omega] Uncaught exception:', err);
});

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1600,
        height: 1000,
        minWidth: 800,
        minHeight: 600,
        show: false, // Don't show until ready-to-show fires (prevents flash)
        frame: false,
        titleBarStyle: 'hidden',
        icon: path.join(__dirname, 'omega.ico'),
        backgroundColor: '#0a0a0a',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
        },
    });

    // Start maximized after content is ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.maximize();
        mainWindow.show();
    });

    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

    if (process.argv.includes('--dev')) {
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    }

    mainWindow.on('closed', () => { mainWindow = null; });
    context.addBreadcrumb('lifecycle', 'Window created');

    // ── Crash Recovery ──────────────────────────────────────
    mainWindow.webContents.on('render-process-gone', (_, details) => {
        console.error(`[Omega] Renderer process gone: ${details.reason} (code: ${details.exitCode})`);
        if (details.reason !== 'clean-exit') {
            console.log('[Omega] Reloading window after renderer crash...');
            setTimeout(() => {
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
                }
            }, 1000);
        }
    });

    mainWindow.on('unresponsive', () => {
        console.warn('[Omega] Window unresponsive');
    });

    mainWindow.on('responsive', () => {
        console.log('[Omega] Window responsive again');
    });

    app.on('child-process-gone', (_, details) => {
        console.error(`[Omega] Child process gone: ${details.type} reason=${details.reason} code=${details.exitCode}`);
    });
}

// ══════════════════════════════════════════════════════════════
// IPC HANDLERS
// ══════════════════════════════════════════════════════════════

function registerIPC() {
    // ── Window Controls ──────────────────────────────────────
    ipcMain.on('window:minimize', () => mainWindow?.minimize());
    ipcMain.on('window:maximize', () => {
        if (mainWindow?.isMaximized()) mainWindow.unmaximize();
        else mainWindow?.maximize();
    });
    ipcMain.on('window:close', () => mainWindow?.close());

    // ── File Operations ──────────────────────────────────────
    ipcMain.handle('file:read', async (_, filePath) => {
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            return { path: filePath, name: path.basename(filePath), content };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:save', async (_, filePath, content) => {
        try {
            const dir = path.dirname(filePath);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(filePath, content, 'utf-8');
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:listDir', async (_, dirPath) => {
        try {
            const entries = fs.readdirSync(dirPath, { withFileTypes: true });
            return entries.map(e => ({
                name: e.name,
                path: path.join(dirPath, e.name),
                isDirectory: e.isDirectory(),
                size: e.isFile() ? fs.statSync(path.join(dirPath, e.name)).size : null,
            }));
        } catch (e) { return []; }
    });

    ipcMain.handle('file:openDialog', async () => {
        const result = await dialog.showOpenDialog(mainWindow, {
            properties: ['openFile'],
            filters: [
                { name: 'All Files', extensions: ['*'] },
                { name: 'Code', extensions: ['js', 'ts', 'py', 'json', 'html', 'css', 'md', 'sol'] },
            ],
        });
        if (result.canceled || result.filePaths.length === 0) return null;
        const filePath = result.filePaths[0];
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            return { path: filePath, name: path.basename(filePath), content };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:openFolder', async () => {
        const result = await dialog.showOpenDialog(mainWindow, { properties: ['openDirectory'] });
        if (result.canceled || result.filePaths.length === 0) return null;
        return result.filePaths[0];
    });

    ipcMain.handle('file:saveDialog', async (_, defaultName) => {
        const result = await dialog.showSaveDialog(mainWindow, {
            defaultPath: defaultName || 'untitled.txt',
        });
        return result.canceled ? null : result.filePath;
    });

    ipcMain.handle('file:exists', async (_, filePath) => fs.existsSync(filePath));

    ipcMain.handle('file:mkdir', async (_, dirPath) => {
        try {
            fs.mkdirSync(dirPath, { recursive: true });
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:delete', async (_, filePath, recursive) => {
        try {
            if (recursive) fs.rmSync(filePath, { recursive: true, force: true });
            else fs.unlinkSync(filePath);
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:rename', async (_, oldPath, newPath) => {
        try {
            fs.renameSync(oldPath, newPath);
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    // ── Terminal (PTY) ───────────────────────────────────────
    ipcMain.handle('terminal:create', async () => {
        if (!ptyModule) return { error: 'node-pty not available' };
        const id = `term-${++terminalCounter}`;
        const shellPath = process.platform === 'win32' ? 'powershell.exe' : (process.env.SHELL || '/bin/bash');
        const pty = ptyModule.spawn(shellPath, [], {
            name: 'xterm-256color',
            cols: 120, rows: 30,
            cwd: process.env.HOME || os.homedir(),
            env: { ...process.env, TERM: 'xterm-256color' },
        });
        terminals.set(id, pty);

        pty.onData((data) => {
            mainWindow?.webContents.send('terminal:data', id, data);
        });
        pty.onExit(({ exitCode }) => {
            mainWindow?.webContents.send('terminal:exit', id, exitCode);
            terminals.delete(id);
        });

        context.addBreadcrumb('lifecycle', `Terminal created: ${id}`);
        return { id, pid: pty.pid };
    });

    ipcMain.on('terminal:input', (_, id, data) => {
        const pty = terminals.get(id);
        if (pty) pty.write(data);
    });

    ipcMain.on('terminal:resize', (_, id, cols, rows) => {
        const pty = terminals.get(id);
        if (pty) try { pty.resize(cols, rows); } catch { }
    });

    ipcMain.on('terminal:kill', (_, id) => {
        const pty = terminals.get(id);
        if (pty) { pty.kill(); terminals.delete(id); }
    });

    // ── File Watcher ─────────────────────────────────────────
    ipcMain.handle('watcher:start', async (_, dirPath) => {
        if (!chokidar) return { error: 'chokidar not available' };
        if (watcher) { await watcher.close(); watcher = null; }
        watcher = chokidar.watch(dirPath, {
            ignored: /(^|[\/\\])(\.git|node_modules|__pycache__|\.pyc$)/,
            persistent: true, depth: 10,
            ignoreInitial: true,
        });
        watcher.on('all', (event, filePath) => {
            mainWindow?.webContents.send('watcher:event', event, filePath);
        });
        return { success: true, path: dirPath };
    });

    // ── Search ───────────────────────────────────────────────
    ipcMain.handle('search:text', async (_, dirPath, query) => {
        const results = [];
        const MAX = 100;
        const SKIP = new Set(['.git', 'node_modules', '__pycache__', '.pyc', 'dist', 'build']);
        const BINARY = new Set(['.png','.jpg','.gif','.exe','.dll','.zip','.gz','.woff','.ttf','.pdf','.mp3','.mp4','.wasm','.ico']);

        function walk(dir, depth) {
            if (depth > 8 || results.length >= MAX) return;
            try {
                const entries = fs.readdirSync(dir, { withFileTypes: true });
                for (const entry of entries) {
                    if (results.length >= MAX) break;
                    if (SKIP.has(entry.name) || entry.name.startsWith('.')) continue;
                    const full = path.join(dir, entry.name);
                    if (entry.isDirectory()) { walk(full, depth + 1); continue; }
                    const ext = path.extname(entry.name).toLowerCase();
                    if (BINARY.has(ext)) continue;
                    try {
                        const content = fs.readFileSync(full, 'utf-8');
                        const lines = content.split('\n');
                        for (let i = 0; i < lines.length && results.length < MAX; i++) {
                            const col = lines[i].indexOf(query);
                            if (col !== -1) {
                                results.push({
                                    file: full, name: entry.name,
                                    line: i + 1, col: col + 1,
                                    text: lines[i].trim().substring(0, 300),
                                });
                            }
                        }
                    } catch { }
                }
            } catch { }
        }
        walk(dirPath, 0);
        return results;
    });

    // ── Backend Bridge ───────────────────────────────────────
    ipcMain.handle('backend:status', async () => bridge.getStatus());

    ipcMain.handle('backend:modules', async () => {
        try { return await bridge.get('/api/modules'); }
        catch { return []; }
    });

    ipcMain.handle('backend:execute', async (_, moduleId, args) => {
        const result = await ipc.executeModule(moduleId, args);
        return result.toJSON();
    });

    ipcMain.handle('backend:describe', async (_, moduleId) => {
        const result = await ipc.describeModule(moduleId);
        return result.toJSON();
    });

    // ── Chat (Agentic) ───────────────────────────────────────
    ipcMain.handle('chat:send', async (_, text, sessionId) => {
        context.addBreadcrumb('chat', `User: ${text.substring(0, 100)}`);

        // Try agentic mode first — agent decides and executes autonomously
        try {
            const result = await agent.processRequest(text);
            context.addBreadcrumb('chat', `Agent response: ${result.type}`);
            // Only return if agent actually succeeded
            if (result.type !== 'error' && result.message && !result.message.includes('empty response')) {
                return result;
            }
            // Agent failed — fall through to direct LLM
            context.addBreadcrumb('chat', 'Agent returned error, trying direct Gemini', {}, 'warning');
        } catch (agentErr) {
            context.addBreadcrumb('chat', `Agent failed: ${agentErr.message}`, {}, 'warning');
        }

        // Fallback: direct chat via backend
        const bridgeReady = await bridge.waitForBridge();
        if (bridgeReady) {
            try {
                const response = await bridge.post('/api/chat', { text, session_id: sessionId });
                return { type: 'chat', message: response.content || response.response || JSON.stringify(response) };
            } catch { }
        }

        // Gemini direct (primary fallback)
        try {
            const response = await _geminiChat(text);
            return { type: 'chat', message: response };
        } catch (geminiErr) {
            context.addBreadcrumb('chat', `Gemini fallback failed: ${geminiErr.message}`, {}, 'warning');
        }

        // Ollama direct (last resort)
        try {
            const response = await _ollamaChat(text);
            return { type: 'chat', message: response };
        } catch (e) {
            return { type: 'chat', message: `Connection error: ${e.message}. Backend, Gemini, and Ollama all unreachable.` };
        }
    });

    ipcMain.handle('chat:abort', async (_, sessionId) => {
        // Signal abort to agent
        agent.abort();
        return { aborted: true };
    });

    ipcMain.handle('chat:tts', async (_, text) => {
        // Proxy TTS request to backend
        const bridgeReady = await bridge.waitForBridge();
        if (!bridgeReady) return { error: 'Backend not ready' };
        try {
            const http = require('http');
            return new Promise((resolve, reject) => {
                const postData = JSON.stringify({ text: text.substring(0, 1000) });
                const req = http.request({
                    hostname: '127.0.0.1', port: bridge.port || 5000,
                    path: '/api/tts', method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) },
                }, (res) => {
                    const chunks = [];
                    res.on('data', c => chunks.push(c));
                    res.on('end', () => {
                        const buf = Buffer.concat(chunks);
                        if (res.statusCode === 200) {
                            resolve({ audio: buf.toString('base64'), mimeType: 'audio/mpeg' });
                        } else {
                            resolve({ error: `TTS failed: ${res.statusCode}` });
                        }
                    });
                });
                req.on('error', e => resolve({ error: e.message }));
                req.write(postData);
                req.end();
            });
        } catch (e) {
            return { error: e.message };
        }
    });

    // ── Agent (Agentic Loop) ─────────────────────────────────
    ipcMain.handle('agent:status', async () => agent.getStatus());
    ipcMain.handle('agent:tools', async () => agent.getToolSchemas());
    ipcMain.handle('agent:approve', async (_, proposalId, confirmText) => {
        return await agent.executeApproved(proposalId, confirmText);
    });
    ipcMain.handle('agent:deny', async (_, proposalId, reason) => {
        return agent.denyProposal(proposalId, reason);
    });
    ipcMain.handle('agent:approve-all', async () => {
        return await agent.executeAllPending();
    });

    // ── Hardware ─────────────────────────────────────────────
    ipcMain.handle('hardware:info', async () => {
        const cpus = os.cpus();
        const info = {
            cpu: { model: cpus[0]?.model, cores: cpus.length, loadAvg: os.loadavg() },
            memory: {
                total: os.totalmem(), free: os.freemem(),
                used: os.totalmem() - os.freemem(),
                percent: ((os.totalmem() - os.freemem()) / os.totalmem() * 100).toFixed(1),
            },
            platform: os.platform(), arch: os.arch(),
            uptime: os.uptime(), hostname: os.hostname(),
        };

        // GPU/VRAM via nvidia-smi (non-blocking best-effort)
        try {
            const nvOut = execSync('nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits', { timeout: 3000, encoding: 'utf-8' });
            const parts = nvOut.trim().split(',').map(s => s.trim());
            if (parts.length >= 5) {
                info.gpu = {
                    name: parts[0],
                    vram_total_mb: parseInt(parts[1]),
                    vram_used_mb: parseInt(parts[2]),
                    vram_free_mb: parseInt(parts[3]),
                    utilization: parseInt(parts[4]),
                };
            }
        } catch { }
        return info;
    });

    // ── Browser Automation ───────────────────────────────────
    ipcMain.handle('browser:navigate', async (_, url) => {
        return await browser.navigate(url);
    });
    ipcMain.handle('browser:screenshot', async (_, name) => {
        return await browser.screenshot(name);
    });
    ipcMain.handle('browser:task', async (_, steps) => {
        return await browser.executeTask(steps);
    });
    ipcMain.handle('browser:close', async () => {
        await browser.close();
        return { closed: true };
    });

    // ── Reports (EasyStreet Pipeline) ────────────────────────
    ipcMain.handle('reports:drafts', async () => {
        try { return await bridge.get('/api/reports/drafts'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('reports:targets', async () => {
        try { return await bridge.get('/api/reports/targets'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('reports:rainmaker', async () => {
        try { return await bridge.get('/api/reports/rainmaker'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('reports:pipeline', async () => {
        try { return await bridge.get('/api/reports/pipeline'); }
        catch { return { error: 'Bridge not connected' }; }
    });

    // ── Security ─────────────────────────────────────────────
    ipcMain.handle('security:scan', async () => {
        try { return await bridge.get('/api/security/scan'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('security:gravity-shield', async (_, action) => {
        try { return await bridge.post('/api/security/shield/gravity', { action }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('security:void', async (_, action) => {
        try { return await bridge.post('/api/security/shield/void', { action }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('security:basilisk', async (_, action) => {
        try { return await bridge.post('/api/security/shield/basilisk', { action }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('security:nemesis', async (_, action) => {
        try { return await bridge.post('/api/security/shield/nemesis', { action }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('security:containment', async () => {
        try { return await bridge.get('/api/security/containment'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('security:processes', async () => {
        try { return await bridge.get('/api/security/processes'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('security:ports', async () => {
        try { return await bridge.get('/api/security/ports'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('security:full-scan', async () => {
        try { return await bridge.post('/api/security/full-scan'); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('security:destroy', async () => {
        try { return await bridge.post('/api/security/destroy'); }
        catch (e) { return { error: e.message }; }
    });

    // ── Tools (Operations) ───────────────────────────────────
    ipcMain.handle('tools:credits', async () => {
        try { return await bridge.get('/api/tools/credits'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('tools:brain', async () => {
        try { return await bridge.get('/api/tools/brain'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('tools:vision', async () => {
        try { return await bridge.get('/api/tools/vision'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('tools:alerts', async (_, req) => {
        try { return await bridge.get('/api/tools/alerts', req); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('tools:send-email', async (_, { to, subject, body }) => {
        try { return await bridge.post('/api/tools/send-email', { to, subject, body }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('tools:code-review', async (_, { repo, pr }) => {
        try { return await bridge.post('/api/tools/code-review', { repo, pr }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('tools:auto-audit', async (_, { repo }) => {
        try { return await bridge.post('/api/tools/auto-audit', { repo }); }
        catch (e) { return { error: e.message }; }
    });

    // ── Ledger ───────────────────────────────────────────────
    ipcMain.handle('ledger:stats', async () => {
        try { return await bridge.get('/api/ledger/stats'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('ledger:search', async (_, query) => {
        try { return await bridge.post('/api/ledger/search', { query }); }
        catch (e) { return { error: e.message }; }
    });

    // ── Vault (Veritas Vault + Mnemo-Cortex) ─────────────────
    ipcMain.handle('vault:search', async (_, query) => {
        try { return await bridge.post('/api/vault/search', { query }); }
        catch (e) { return { error: e.message }; }
    });
    ipcMain.handle('vault:context', async () => {
        try { return await bridge.get('/api/vault/context'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('vault:sessions', async () => {
        try { return await bridge.get('/api/vault/sessions'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('vault:ki-health', async () => {
        try { return await bridge.get('/api/vault/ki-health'); }
        catch { return { error: 'Bridge not connected' }; }
    });
    ipcMain.handle('vault:sweep', async () => {
        try { return await bridge.post('/api/vault/sweep'); }
        catch (e) { return { error: e.message }; }
    });
}

// ── Direct Ollama Chat (Fallback) ────────────────────────────

// ── Direct Gemini Chat (Primary Fallback) ────────────────────

let _cachedGeminiKey = null;

async function _getGeminiKey() {
    if (_cachedGeminiKey) return _cachedGeminiKey;
    // Env variable
    if (process.env.GEMINI_API_KEY) { _cachedGeminiKey = process.env.GEMINI_API_KEY; return _cachedGeminiKey; }
    // gcloud Secret Manager
    try {
        const key = execSync('gcloud secrets versions access latest --secret=GEMINI_API_KEY', { timeout: 10000, encoding: 'utf-8' }).trim();
        if (key && key.length > 10) { _cachedGeminiKey = key; console.log('[Omega] Gemini key loaded'); return key; }
    } catch { }
    // .env file
    try {
        const envPath = path.join(__dirname, '.env');
        if (fs.existsSync(envPath)) {
            for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
                const m = line.match(/^GEMINI_API_KEY\s*=\s*(.+)/);
                if (m) { _cachedGeminiKey = m[1].trim().replace(/^["']|["']$/g, ''); return _cachedGeminiKey; }
            }
        }
    } catch { }
    return null;
}

function _geminiChat(text) {
    return new Promise(async (resolve, reject) => {
        const key = await _getGeminiKey();
        if (!key) return reject(new Error('No Gemini API key'));
        const https = require('https');
        const payload = JSON.stringify({
            system_instruction: { parts: [{ text: 'You are Omega, a powerful AI assistant inside the Gravity Omega IDE. Be direct, helpful, and precise. You have access to tools and can execute code.' }] },
            contents: [{ role: 'user', parts: [{ text }] }],
            generationConfig: { temperature: 0.3, maxOutputTokens: 4096, topP: 0.95 },
        });
        const model = 'gemini-2.5-flash';
        const req = https.request({
            hostname: 'generativelanguage.googleapis.com',
            path: `/v1beta/models/${model}:generateContent?key=${key}`,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            timeout: 120000,
        }, (res) => {
            let data = '';
            res.on('data', (c) => data += c);
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    const content = parsed.candidates?.[0]?.content?.parts?.[0]?.text;
                    if (content) resolve(content);
                    else if (parsed.error) reject(new Error(parsed.error.message));
                    else resolve('(empty response)');
                } catch { resolve(data); }
            });
        });
        req.on('error', reject);
        req.on('timeout', () => { req.destroy(); reject(new Error('Gemini timeout')); });
        req.write(payload);
        req.end();
    });
}

function _ollamaChat(text) {
    return new Promise((resolve, reject) => {
        const http = require('http');
        const payload = JSON.stringify({
            model: 'qwen2.5:7b',
            messages: [
                { role: 'system', content: 'You are Omega, a powerful local AI assistant. Be direct, helpful, and precise.' },
                { role: 'user', content: text },
            ],
            stream: false,
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
                    resolve(parsed.message?.content || data);
                } catch { resolve(data); }
            });
        });
        req.on('error', reject);
        req.on('timeout', () => { req.destroy(); reject(new Error('Ollama timeout')); });
        req.write(payload);
        req.end();
    });
}

// ── Menu ─────────────────────────────────────────────────────

function buildMenu() {
    const template = [
        {
            label: 'File',
            submenu: [
                { label: 'Open File...', accelerator: 'CmdOrCtrl+O', click: () => mainWindow?.webContents.send('menu:open-file') },
                { label: 'Open Folder...', click: () => mainWindow?.webContents.send('menu:open-folder') },
                { type: 'separator' },
                { label: 'Save', accelerator: 'CmdOrCtrl+S', click: () => mainWindow?.webContents.send('menu:save') },
                { type: 'separator' },
                { role: 'quit' },
            ],
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' }, { role: 'redo' }, { type: 'separator' },
                { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' },
            ],
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' },
                { role: 'zoomIn' }, { role: 'zoomOut' }, { role: 'resetZoom' },
                { type: 'separator' }, { role: 'togglefullscreen' },
            ],
        },
        {
            label: 'Terminal',
            submenu: [
                { label: 'New Terminal', accelerator: 'Ctrl+`', click: () => mainWindow?.webContents.send('menu:new-terminal') },
            ],
        },
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── Protocol Scheme ──────────────────────────────────────────

try {
    protocol.registerSchemesAsPrivileged([
        {
            scheme: 'omega-file',
            privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: false },
        },
    ]);
} catch (e) {
    console.warn('[Omega] Protocol registration failed:', e.message);
}

// ── App Ready ────────────────────────────────────────────────

app.whenReady().then(async () => {
    protocol.registerFileProtocol('omega-file', (request, callback) => {
        const filePath = decodeURIComponent(request.url.replace('omega-file://', ''));
        callback({ path: filePath });
    });

    registerIPC();
    buildMenu();
    createWindow();

    // Git auto-update (silent, non-blocking)
    try {
        const { execFile } = require('child_process');
        execFile('git', ['pull', '--ff-only'], { cwd: __dirname, windowsHide: true }, (err, stdout) => {
            if (!err) {
                const msg = (stdout || '').trim();
                if (msg && msg !== 'Already up to date.') {
                    console.log(`[Omega] Auto-updated: ${msg}`);
                    context.addBreadcrumb('lifecycle', `Auto-update: ${msg}`);
                }
            }
        });
    } catch { }

    context.addBreadcrumb('lifecycle', 'App ready, window created');

    // Start Python backend
    bridge.on('status', (status) => {
        context.addBreadcrumb('lifecycle', `Bridge status: ${status}`);
        mainWindow?.webContents.send('omega:bridge-status-change', status);
    });

    bridge.on('ready', async (info) => {
        context.addBreadcrumb('lifecycle', `Backend READY on port ${info.port}`, info);
        await hooks.fire('on_backend_ready', bridge.getStatus());
        mainWindow?.webContents.send('omega:backend-ready', info);
    });

    bridge.on('error', async (err) => {
        context.addBreadcrumb('lifecycle', `Backend ERROR: ${err.message}`, {}, 'error');
        await hooks.fire('on_backend_error', err);
    });

    bridge.on('sentinel-alert', (alert) => {
        context.addBreadcrumb('sentinel', `[${alert.severity}] ${alert.message}`);
        mainWindow?.webContents.send('omega:sentinel-alert', alert);
        // Log critical events (auto-heals) as permanent breadcrumbs
        if (alert.severity === 'critical') {
            console.warn(`[SENTINEL] CRITICAL: ${alert.message}`);
        }
    });

    bridge.start().catch((err) => {
        console.warn(`[Omega] Backend did not start: ${err.message}`);
        console.warn('[Omega] Chat will use Ollama directly as fallback');
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    crashLog(`window-all-closed fired, platform=${process.platform}`);
    if (process.platform !== 'darwin') app.quit();
});

// ── Graceful Shutdown ────────────────────────────────────────

app.on('before-quit', async () => {
    crashLog('before-quit fired');
    console.log('[Omega] before-quit fired');
    context.addBreadcrumb('lifecycle', 'Shutting down');
    await hooks.fire('on_shutdown');

    for (const [id, term] of terminals) {
        try { term.kill(); } catch { }
    }
    terminals.clear();

    await browser.close();
    await bridge.stop();
    await context.close();
});

process.on('exit', (code) => {
    crashLog(`process.exit code=${code}`);
    console.log(`[Omega] Process exit with code: ${code}`);
});

process.on('beforeExit', (code) => {
    crashLog(`process.beforeExit code=${code}`);
    console.log(`[Omega] beforeExit with code: ${code}`);
});

process.on('SIGTERM', () => { crashLog('SIGTERM received'); });
process.on('SIGINT', () => { crashLog('SIGINT received'); });
