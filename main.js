/**
 * GRAVITY OMEGA v2.0 — Electron Main Process
 * Ported from Windows → WSL Ubuntu
 *
 * Architecture:
 *   main.js → preload.js → renderer (app.js)
 *   main.js → OmegaBridge → Python web_server.py (port 5000)
 *   main.js → OmegaAgent → Agentic Loop (Gemini/Ollama)
 */
const { app, BrowserWindow, ipcMain, dialog, Menu, protocol, shell, globalShortcut } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn, execSync } = require('child_process');

// ── CRASH DIAGNOSTICS — write to file since stdout may not flush ──
const CRASH_LOG = path.join(os.tmpdir(), 'gravity_omega_crash.log');
function crashLog(msg) {
    try {
        const stats = fs.statSync(CRASH_LOG);
        if (stats.size > 1024 * 1024) {
            fs.renameSync(CRASH_LOG, `${CRASH_LOG}.old`);
        }
    } catch {}
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
const { ConversationStore } = require('./omega/conversation_store');
const { startServer: startMcpServer } = require('./omega/omega_mcp_server');
const { OCRHandler } = require('./ocr_module/ocr_handler');

// ── Global Instances ─────────────────────────────────────────
const bridge = new OmegaBridge();
const ipc = new OmegaIPC(bridge);
const context = new OmegaContext();
const hooks = new OmegaHooks();
// NDJSON audit log path — written by ApprovalGate on every audit event.
// Lives under ~/.veritas/ so it survives across reinstalls and is shared
// with the rest of the VERITAS toolchain.
const AUDIT_LOG_PATH = path.join(os.homedir(), '.veritas', 'audit.ndjson');
const agent = new OmegaAgent({
    context, hooks, bridge,
    userName: process.env.GRAVITY_OMEGA_USER || 'RJ',
    auditLogPath: AUDIT_LOG_PATH,
});
const browser = new OmegaBrowser({ screenshotDir: path.join(__dirname, 'screenshots') });
const ocrHandler = new OCRHandler();
let conversationStore = null; // initialized after app.whenReady()

// v4.2: Forward agent progress events to renderer for live thinking indicator
agent.onProgress = (event) => {
    try {
        if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
            mainWindow.webContents.send('omega:agent-step', event);
            // v4.3: Auto-open files in Monaco when agent writes them
            if (event.phase === 'tool_done' && event.ok && event.tool) {
                let filePath = '';
                const tool = event.tool;
                // Only auto-open for actual file writes (MUT:AST) or UI open commands (MUT:UI)
                if (tool === 'MUT:AST' || tool === 'writeFile' || tool === 'RUN:writeFile' || tool === 'CREATE:AST' || tool === 'editFile') {
                    filePath = typeof event.args === 'string' ? event.args : (event.args?.result?.path || event.args?.path || '');
                } else if (tool === 'MUT:UI' || tool === 'REQ:UI' || tool === 'openFile') {
                    // For UI tools, path is in args (string) or args.path
                    if (typeof event.args === 'string') {
                        filePath = event.args.replace(/^open:/, '').replace(/^['"]|['"]$/g, '').trim();
                    } else if (event.args?.path) {
                        filePath = event.args.path;
                    }
                } else if (tool === 'openTerminal') {
                    // Send to renderer directly and skip file opening
                    console.log(`[MAIN IPC DEBUG] Forwarding openTerminal to renderer with command: ${event.args.command || '(empty)'}`);
                    mainWindow.webContents.send('omega:open-terminal', { command: event.args.command });
                    return;
                }
                
                console.log(`[MAIN IPC DEBUG] tool_done received. Tool: ${tool}, Extracted filePath: "${filePath}"`);
                
                const path = require('path');
                if (filePath && path.extname(filePath.trim()).length > 0) {
                    filePath = filePath.trim();
                    if (!path.isAbsolute(filePath)) {
                        filePath = path.resolve(process.cwd(), filePath);
                    }
                    console.log(`[MAIN IPC] Agent wrote file, triggering auto-open: ${filePath}`);
                    mainWindow.webContents.send('omega:open-file', filePath);
                }
            }
        }
    } catch (e) { console.error('[IPC] agent-step error:', e.message); }
};

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

let ipcRegistered = false;

// (GPU flags removed — native Windows Electron handles GPU properly)

// ══════════════════════════════════════════════════════════════
// WINDOW
// ══════════════════════════════════════════════════════════════

// Prevent multiple windows — hard-exit if another instance is already running
const gotLock = app.requestSingleInstanceLock();
crashLog(`Single instance lock: gotLock=${gotLock}`);
if (!gotLock) {
    crashLog('EXITING: second instance detected, calling app.quit()');
    app.quit();
    // CRITICAL: return/exit immediately so app.whenReady() never fires
    return;
}
app.on('second-instance', () => {
    crashLog('second-instance event fired');
    if (mainWindow) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        if (!mainWindow.isVisible()) {
            mainWindow.maximize();
            mainWindow.show();
        }
        mainWindow.focus();
    }
});

// Catch EPIPE and other stream errors that crash Electron
process.on('uncaughtException', (err) => {
    crashLog(`UNCAUGHT EXCEPTION: ${err.code || ''} ${err.message} ${err.stack || ''}`);
    if (err.code === 'EPIPE' || err.code === 'ERR_STREAM_DESTROYED') {
        console.warn('[Omega] Caught stream error (non-fatal):', err.code);
        return; // swallow — pipe broke, not a real crash
    }
    console.error('[Omega] Uncaught exception:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    crashLog(`UNHANDLED REJECTION: ${reason?.message || reason} ${reason?.stack || ''}`);
    console.error('[Omega] Unhandled rejection at promise:', reason);
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
            sandbox: true,       // Renderer process in OS sandbox; preload only uses ipcRenderer/contextBridge
            webviewTag: false,   // Disable <webview> — media uses iframes inside controlled panels instead
        },
    });

    // Start maximized after content is ready
    mainWindow.once('ready-to-show', () => {
        if (!process.argv.includes('--daemon')) {
            mainWindow.maximize();
            mainWindow.show();
        } else {
            console.log('[Omega] Running in headless daemon mode.');
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

    if (process.argv.includes('--dev')) {
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    }

    mainWindow.on('closed', () => { mainWindow = null; });

    // ── Prevent duplicate windows from popups, target="_blank", or webview allowpopups ──
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        crashLog(`Blocked new window request: ${url}`);
        console.log(`[Omega] Blocked popup window, opening in browser: ${url}`);
        if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
            shell.openExternal(url);
        }
        return { action: 'deny' };
    });

    context.addBreadcrumb('lifecycle', 'Window created');

    // ── Crash Recovery (with crash-loop protection) ────────
    // Track renderer crashes within a 60s window. After 3 crashes in that
    // window, stop auto-reloading and surface a dialog so the user can
    // pick safe-mode or quit. Without this, a renderer that crashes on
    // every load gets stuck in an infinite reload loop.
    const _rendererCrashes = [];
    const CRASH_WINDOW_MS = 60_000;
    const CRASH_LIMIT = 3;
    mainWindow.webContents.on('render-process-gone', (_, details) => {
        console.error(`[Omega] Renderer process gone: ${details.reason} (code: ${details.exitCode})`);
        if (details.reason === 'clean-exit') return;

        const now = Date.now();
        // Drop crashes older than the window
        while (_rendererCrashes.length && now - _rendererCrashes[0] > CRASH_WINDOW_MS) _rendererCrashes.shift();
        _rendererCrashes.push(now);

        if (_rendererCrashes.length >= CRASH_LIMIT) {
            crashLog(`Crash loop detected: ${_rendererCrashes.length} crashes in ${CRASH_WINDOW_MS}ms — stopping auto-reload`);
            console.error(`[Omega] Crash loop detected (${_rendererCrashes.length} in ${CRASH_WINDOW_MS / 1000}s) — refusing to auto-reload`);
            const choice = dialog.showMessageBoxSync(mainWindow, {
                type: 'error',
                buttons: ['Open DevTools', 'Reload Anyway', 'Quit'],
                defaultId: 0,
                cancelId: 2,
                title: 'Gravity Omega — renderer crash loop',
                message: 'The UI has crashed repeatedly.',
                detail: `${_rendererCrashes.length} renderer crashes in the last ${CRASH_WINDOW_MS / 1000}s. Last reason: ${details.reason}.\n\nOpening DevTools is recommended to inspect the console error before continuing.`,
            });
            if (choice === 0) { try { mainWindow.webContents.openDevTools({ mode: 'detach' }); } catch {} }
            else if (choice === 1) { _rendererCrashes.length = 0; mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html')); }
            else { app.quit(); }
            return;
        }

        console.log(`[Omega] Reloading window after renderer crash (${_rendererCrashes.length}/${CRASH_LIMIT})...`);
        setTimeout(() => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
            }
        }, 1000);
    });

    mainWindow.on('unresponsive', () => {
        console.warn('[Omega] Window unresponsive');
    });

    mainWindow.on('responsive', () => {
        console.log('[Omega] Window responsive again');
    });

    app.once('child-process-gone', (_, details) => {
        console.error(`[Omega] Child process gone: ${details.type} reason=${details.reason} code=${details.exitCode}`);
    });
}

// ══════════════════════════════════════════════════════════════
// IPC HANDLERS
// ══════════════════════════════════════════════════════════════

// ── Path Safety ─────────────────────────────────────────────
// Validates a renderer-supplied path before touching the filesystem.
// Guards against null-byte injection, excessively long strings, and
// non-string types. Does NOT restrict which directories are accessible
// (this is a general-purpose editor) — shell injection is prevented
// separately by using spawn() with array args instead of execSync.
function isSafePath(p) {
    if (typeof p !== 'string') return false;
    if (p.length === 0 || p.length > 4096) return false;
    if (p.includes('\0')) return false; // null-byte injection
    return true;
}

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
        if (!isSafePath(filePath)) return { error: 'Invalid path' };
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            return { path: filePath, name: path.basename(filePath), content };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:save', async (_, filePath, content) => {
        if (!isSafePath(filePath)) return { error: 'Invalid path' };
        if (typeof content !== 'string') return { error: 'Invalid content' };
        try {
            const dir = path.dirname(filePath);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            const tmp = `${filePath}.tmp${Date.now()}`;
            fs.writeFileSync(tmp, content, 'utf-8');
            fs.renameSync(tmp, filePath);
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:listDir', async (_, dirPath) => {
        if (!isSafePath(dirPath)) return [];
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

    // Media: shared folder scan (fully async — never blocks main process)
    async function scanAudioFolder(dir) {
        const audioExts = new Set(['.mp3', '.m4a', '.m4b', '.ogg', '.wav', '.flac', '.aac', '.wma', '.aax', '.aaxc']);
        const fsp = require('fs').promises;

        async function walkDir(currentDir) {
            let entries = [];
            try { entries = await fsp.readdir(currentDir, { withFileTypes: true }); } catch (_) { return []; }
            let results = [];
            for (const entry of entries) {
                const fullPath = path.join(currentDir, entry.name);
                if (entry.isDirectory()) {
                    const sub = await walkDir(fullPath);
                    results = results.concat(sub);
                } else if (entry.isFile()) {
                    const ext = path.extname(entry.name).toLowerCase();
                    if (audioExts.has(ext)) {
                        const relPath = path.relative(dir, fullPath);
                        const displayName = relPath.includes(path.sep) ? relPath : entry.name;
                        results.push({ name: displayName, path: fullPath });
                    }
                }
            }
            return results;
        }

        try {
            const files = (await walkDir(dir)).sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
            console.log(`[MEDIA] Scanned ${dir}: ${files.length} audio files found`);
            return { dir, files, converted: [] };
        } catch (e) { return { dir, files: [], error: e.message }; }
    }

    // Media: open folder via dialog
    ipcMain.handle('media:openAudioFolder', async () => {
        const result = await dialog.showOpenDialog(mainWindow, { properties: ['openDirectory'] });
        if (result.canceled || result.filePaths.length === 0) return null;
        return await scanAudioFolder(result.filePaths[0]);
    });

    // Media: scan a saved folder path (no dialog — for auto-scan on startup)
    ipcMain.handle('media:scanFolder', async (_, folderPath) => {
        if (!isSafePath(folderPath) || !fs.existsSync(folderPath)) return null;
        return await scanAudioFolder(folderPath);
    });

    // Media: decrypt AAX → M4B (fast remux, no re-encode)
    ipcMain.handle('media:decryptAAX', async (_, aaxPath) => {
        if (!isSafePath(aaxPath) || !fs.existsSync(aaxPath)) return null;
        const ext = path.extname(aaxPath).toLowerCase();
        if (ext !== '.aax') return aaxPath; // Not AAX, return as-is

        const m4bPath = aaxPath.replace(/\.aax$/i, '.m4b');
        if (fs.existsSync(m4bPath)) return m4bPath; // Already converted

        // Read activation bytes
        let ab = '';
        const abPath = path.join(os.homedir(), '.veritas', 'audible_activation_bytes.txt');
        try { ab = fs.readFileSync(abPath, 'utf-8').trim(); } catch (_) {}
        if (!ab) {
            console.error('[MEDIA] No activation bytes found at', abPath);
            return null;
        }

        console.log(`[MEDIA] Decrypting: ${path.basename(aaxPath)}`);
        try {
            await new Promise((resolve, reject) => {
                const proc = spawn('ffmpeg', ['-y', '-activation_bytes', ab, '-i', aaxPath, '-c', 'copy', m4bPath], { stdio: 'pipe' });
                const timer = setTimeout(() => { proc.kill(); reject(new Error('timeout')); }, 300000);
                proc.on('close', (code) => { clearTimeout(timer); code === 0 ? resolve() : reject(new Error(`ffmpeg exit ${code}`)); });
                proc.on('error', (e) => { clearTimeout(timer); reject(e); });
            });
            if (fs.existsSync(m4bPath) && fs.statSync(m4bPath).size > 1000) {
                console.log(`[MEDIA] Decrypted: ${path.basename(m4bPath)}`);
                return m4bPath;
            }
            return null;
        } catch (e) {
            console.error(`[MEDIA] Decrypt failed:`, e.message?.slice(0, 200));
            try { fs.unlinkSync(m4bPath); } catch (_) {}
            return null;
        }
    });

    // Media: extract metadata from audio file via ffprobe
    ipcMain.handle('media:getMetadata', async (_, filePath) => {
        if (!isSafePath(filePath) || !fs.existsSync(filePath)) return null;
        try {
            const raw = await new Promise((resolve, reject) => {
                let out = '';
                const proc = spawn('ffprobe', ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filePath], { stdio: ['ignore', 'pipe', 'pipe'] });
                const timer = setTimeout(() => { proc.kill(); reject(new Error('timeout')); }, 15000);
                proc.stdout.on('data', d => out += d);
                proc.on('close', (code) => { clearTimeout(timer); code === 0 ? resolve(out) : reject(new Error(`ffprobe exit ${code}`)); });
                proc.on('error', (e) => { clearTimeout(timer); reject(e); });
            });
            const data = JSON.parse(raw);
            const fmt = data.format || {};
            const tags = fmt.tags || {};
            // Normalize tag keys (some are uppercase, some lowercase)
            const t = {};
            for (const [k, v] of Object.entries(tags)) { t[k.toLowerCase()] = v; }
            return {
                title: t.title || t.name || null,
                artist: t.artist || t.album_artist || t.author || null,
                album: t.album || null,
                genre: t.genre || null,
                duration: fmt.duration ? parseFloat(fmt.duration) : null,
                narrator: t.narrator || t.composer || null,
                year: t.date || t.year || null
            };
        } catch (_) { return null; }
    });

    // Media: extract cover art from audio file
    const coverDir = path.join(os.homedir(), '.veritas', 'covers');
    ipcMain.handle('media:getCoverArt', async (_, filePath) => {
        if (!isSafePath(filePath) || !fs.existsSync(filePath)) return null;
        try {
            if (!fs.existsSync(coverDir)) fs.mkdirSync(coverDir, { recursive: true });
            // Use filename hash as cache key
            const crypto = require('crypto');
            const hash = crypto.createHash('md5').update(filePath).digest('hex').substring(0, 12);
            const coverPath = path.join(coverDir, hash + '.jpg');
            if (fs.existsSync(coverPath)) {
                return 'file://' + coverPath.replace(/\\/g, '/');
            }
            // Extract with ffmpeg — spawn with array args (no shell interpolation)
            await new Promise((resolve, reject) => {
                const proc = spawn('ffmpeg', ['-y', '-i', filePath, '-an', '-vcodec', 'mjpeg', '-frames:v', '1', coverPath], { stdio: 'pipe' });
                const timer = setTimeout(() => { proc.kill(); reject(new Error('timeout')); }, 15000);
                proc.on('close', (code) => { clearTimeout(timer); resolve(code); });
                proc.on('error', (e) => { clearTimeout(timer); reject(e); });
            });
            if (fs.existsSync(coverPath) && fs.statSync(coverPath).size > 100) {
                return 'file://' + coverPath.replace(/\\/g, '/');
            }
            // Cleanup zero-byte files
            try { fs.unlinkSync(coverPath); } catch (_) {}
            return null;
        } catch (_) { return null; }
    });

    // Media: persistent state
    const mediaStatePath = path.join(os.homedir(), '.veritas', 'media_state.json');
    const audiobookLibrary = path.join(os.homedir(), '.veritas', 'audiobooks');

    ipcMain.handle('media:saveState', async (_, state) => {
        try {
            const dir = path.dirname(mediaStatePath);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(mediaStatePath, JSON.stringify(state, null, 2), 'utf-8');
            return { ok: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('media:loadState', async () => {
        try {
            if (!fs.existsSync(mediaStatePath)) return null;
            return JSON.parse(fs.readFileSync(mediaStatePath, 'utf-8'));
        } catch (e) { return null; }
    });

    ipcMain.handle('media:importToLibrary', async (_, srcPath) => {
        if (!isSafePath(srcPath)) return { error: 'Invalid path' };
        try {
            if (!fs.existsSync(audiobookLibrary)) fs.mkdirSync(audiobookLibrary, { recursive: true });
            const fileName = path.basename(srcPath);
            const destPath = path.join(audiobookLibrary, fileName);
            if (!fs.existsSync(destPath)) {
                console.log(`[MEDIA] Importing to library: ${fileName}`);
                fs.copyFileSync(srcPath, destPath);
            }
            return { name: fileName, path: destPath, imported: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:saveDialog', async (_, defaultName) => {
        const result = await dialog.showSaveDialog(mainWindow, {
            defaultPath: defaultName || 'untitled.txt',
        });
        return result.canceled ? null : result.filePath;
    });

    ipcMain.handle('file:exists', async (_, filePath) => {
        if (!isSafePath(filePath)) return false;
        return fs.existsSync(filePath);
    });

    ipcMain.handle('file:mkdir', async (_, dirPath) => {
        if (!isSafePath(dirPath)) return { error: 'Invalid path' };
        try {
            fs.mkdirSync(dirPath, { recursive: true });
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:delete', async (_, filePath, recursive) => {
        if (!isSafePath(filePath)) return { error: 'Invalid path' };
        try {
            if (recursive) fs.rmSync(filePath, { recursive: true, force: true });
            else fs.unlinkSync(filePath);
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    ipcMain.handle('file:rename', async (_, oldPath, newPath) => {
        if (!isSafePath(oldPath) || !isSafePath(newPath)) return { error: 'Invalid path' };
        try {
            fs.renameSync(oldPath, newPath);
            return { success: true };
        } catch (e) { return { error: e.message }; }
    });

    // ── Terminal (PTY) ───────────────────────────────────────
    const MAX_TERMINALS = 20;
    ipcMain.handle('terminal:create', async () => {
        if (!ptyModule) return { error: 'node-pty not available — terminal support requires a Windows build of node-pty' };
        if (terminals.size >= MAX_TERMINALS) return { error: `Terminal limit reached (max ${MAX_TERMINALS})` };

        const cwd = (() => {
            const candidate = process.env.HOME || os.homedir();
            try { return fs.existsSync(candidate) ? candidate : os.tmpdir(); } catch { return os.tmpdir(); }
        })();

        const shellPath = process.platform === 'win32' ? 'powershell.exe' : (process.env.SHELL || '/bin/bash');
        const id = `term-${++terminalCounter}`;
        let pty;
        try {
            pty = ptyModule.spawn(shellPath, [], {
                name: 'xterm-256color',
                cols: 120, rows: 30,
                cwd,
                env: { ...process.env, TERM: 'xterm-256color' },
            });
        } catch (spawnErr) {
            console.error('[PTY] Spawn failed:', spawnErr.message);
            return { error: `Shell spawn failed: ${spawnErr.message}` };
        }

        terminals.set(id, pty);

        pty.onData((data) => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('terminal:data', id, data);
            }
        });
        pty.onExit(({ exitCode }) => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('terminal:exit', id, exitCode);
            }
            pty.removeAllListeners();
            terminals.delete(id);
        });

        context.addBreadcrumb('lifecycle', `Terminal created: ${id} shell=${shellPath} cwd=${cwd}`);
        return { id, pid: pty.pid };
    });

    ipcMain.on('terminal:input', (_, id, data) => {
        const pty = terminals.get(id);
        if (pty) pty.write(data);
    });

    ipcMain.on('terminal:resize', (_, id, cols, rows) => {
        if (!Number.isInteger(cols) || !Number.isInteger(rows)) return;
        if (cols < 10 || cols > 500 || rows < 3 || rows > 200) return;
        const pty = terminals.get(id);
        if (pty) try { pty.resize(cols, rows); } catch { }
    });

    ipcMain.on('terminal:kill', (_, id) => {
        const pty = terminals.get(id);
        if (pty) { pty.kill(); terminals.delete(id); }
    });

    ipcMain.handle('terminal:list', async () => {
        return Array.from(terminals.entries()).map(([id, pty]) => ({ id, pid: pty.pid }));
    });

    ipcMain.handle('watcher:stop', async () => {
        if (watcher) { await watcher.close(); watcher = null; }
        return { success: true };
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
        if (!isSafePath(dirPath) || typeof query !== 'string' || query.length === 0 || query.length > 500) return [];
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
    ipcMain.handle('chat:send', async (_, text, sessionId, model, attachments = []) => {
        context.addBreadcrumb('chat', `User: ${text.substring(0, 100)}`);

        // v6.0: Hydrate agent memory from persistent conversation store on every request
        if (conversationStore && sessionId) {
            try {
                const thread = conversationStore.loadThread(sessionId);
                if (thread && thread.messages && thread.messages.length > 0) {
                    agent.setThreadHistory(thread.messages);
                    console.log(`[AGENT] Hydrated thread ${sessionId} with ${thread.messages.length} messages from store`);
                }
            } catch (err) {
                console.warn('[AGENT] Thread hydration failed (non-fatal):', err.message);
            }
        }

        let agentErrorStr = null;
        try {
            const result = await agent.processRequest(text, model, attachments);
            // v4.3.19e: Auto-open HTML dashboards in browser after successful task completion
            // Uses Electron's shell.openPath — the only reliable way in the main process
            if (result.type !== 'error' && result.steps > 0) {
                try {
                    const stepLog = result.stepLog || [];
                    const touchedDirs = new Set();
                    for (const step of stepLog) {
                        const a = typeof step.args === 'string' ? step.args : (step.args?.prm || '');
                        const cleaned = a.replace(/['"]/g, '').trim();
                        const m = cleaned.match(/([A-Za-z]:\\[^\s]+)/);
                        if (m) {
                            const dir = path.dirname(m[1]);
                            if (dir && dir.length > 3 && fs.existsSync(dir)) touchedDirs.add(dir);
                        }
                    }
                    let bestHtml = null, bestMtime = 0;
                    for (const dir of touchedDirs) {
                        try {
                            for (const file of fs.readdirSync(dir)) {
                                if (!/\.html?$/i.test(file) || /template/i.test(file)) continue;
                                const full = path.join(dir, file);
                                const stat = fs.statSync(full);
                                if ((Date.now() - stat.mtimeMs) < 300000 && stat.mtimeMs > bestMtime) {
                                    const head = fs.readFileSync(full, 'utf8').substring(0, 500);
                                    if (!head.includes('{{') && head.includes('<html')) {
                                        bestMtime = stat.mtimeMs;
                                        bestHtml = full;
                                    }
                                }
                            }
                        } catch (e) { /* skip unreadable dirs */ }
                    }
                    if (bestHtml) {
                        console.log('[AUTO-OPEN] Opening HTML in browser:', bestHtml);
                        shell.openPath(bestHtml).then(errMsg => {
                            if (errMsg) console.warn('[AUTO-OPEN] shell.openPath error:', errMsg);
                            else console.log('[AUTO-OPEN] Success:', bestHtml);
                        });
                    }
                } catch (autoOpenErr) {
                    console.warn('[AUTO-OPEN] Scan error:', autoOpenErr.message);
                }
            }
            // Agent failed before doing any work — return the exact structured error
            if (result.type === 'error') {
                return result;
            }

            // v5.0: [OPTIMIZATION] IPC Race Condition & Bottleneck mitigation.
            // Strip massive token-streaming artifacts (like full file contents in arguments or outputs)
            // from the stepLog before passing across the IPC bridge, as it blocks the UI thread during serialization.
            if (result.stepLog && Array.isArray(result.stepLog)) {
                result.stepLog = result.stepLog.map(step => {
                    const cleanStep = { ...step };

                    // Since the UI purely uses stepLog for visual rendering, we replace giant payloads
                    // with a placeholder to avoid JSON parse crashes or blocking the IPC channel.
                    if (cleanStep.args) {
                        if (typeof cleanStep.args === 'string' && cleanStep.args.length > 1000) {
                            cleanStep.args = cleanStep.args.substring(0, 1000) + '... [IPC truncated]';
                        } else if (typeof cleanStep.args === 'object' && cleanStep.args !== null && !Array.isArray(cleanStep.args)) {
                            const clone = { ...cleanStep.args };
                            for (const k of Object.keys(clone)) {
                                if (typeof clone[k] === 'string' && clone[k].length > 1000) {
                                    clone[k] = clone[k].substring(0, 1000) + '... [IPC truncated]';
                                }
                            }
                            cleanStep.args = clone;
                        }
                    }

                    if (cleanStep.result) {
                        if (typeof cleanStep.result === 'string' && cleanStep.result.length > 1000) {
                            cleanStep.result = cleanStep.result.substring(0, 1000) + '... [IPC truncated]';
                        } else if (typeof cleanStep.result === 'object' && cleanStep.result !== null && !Array.isArray(cleanStep.result)) {
                            const cleanResult = { ...cleanStep.result };
                            if (cleanResult.output && typeof cleanResult.output === 'string') {
                                cleanResult.output = cleanResult.output.length > 1000 ? cleanResult.output.substring(0, 1000) + '... [IPC truncated]' : cleanResult.output;
                            }
                            if (cleanResult.data && typeof cleanResult.data === 'string') {
                                cleanResult.data = cleanResult.data.length > 1000 ? cleanResult.data.substring(0, 1000) + '... [IPC truncated]' : cleanResult.data;
                            }
                            cleanStep.result = cleanResult;
                        }
                    }
                    return cleanStep;
                });
            }

            return result;
        } catch (agentErr) {
            context.addBreadcrumb('chat', `Agent failed: ${agentErr.message}`, {}, 'warning');
            return { type: 'error', message: `Agent Crash: ${agentErr.message}\n\nNo fallback available. Agent must resolve this constraint.` };
        }
    });

    ipcMain.handle('chat:abort', async (_, sessionId) => {
        // Signal abort to agent
        agent.abort();
        return { aborted: true };
    });

    ipcMain.handle('chat:tts', async (_, text) => {
        console.log('[TTS:main] Request received, text length:', text?.length);
        // Proxy TTS request to backend
        const bridgeReady = await bridge.waitForBridge();
        console.log('[TTS:main] Bridge ready:', bridgeReady, 'port:', bridge._port);
        if (!bridgeReady) return { error: 'Backend not ready' };
        try {
            const http = require('http');
            return new Promise((resolve, reject) => {
                const postData = JSON.stringify({ text: text.substring(0, 1000) });
                const req = http.request({
                    hostname: '127.0.0.1', port: bridge._port || 5000,
                    path: '/api/tts', method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) },
                    timeout: 30000,
                }, (res) => {
                    console.log('[TTS:main] Response status:', res.statusCode);
                    const chunks = [];
                    res.on('data', c => chunks.push(c));
                    res.on('end', () => {
                        const buf = Buffer.concat(chunks);
                        console.log('[TTS:main] Response body size:', buf.length, 'bytes');
                        if (res.statusCode === 200) {
                            resolve({ audio: buf.toString('base64'), mimeType: 'audio/mpeg' });
                        } else {
                            const errBody = buf.toString('utf-8').substring(0, 200);
                            console.error('[TTS:main] Error response:', errBody);
                            resolve({ error: `TTS failed: ${res.statusCode} ${errBody}` });
                        }
                    });
                });
                req.on('error', e => {
                    console.error('[TTS:main] Request error:', e.message);
                    resolve({ error: e.message });
                });
                req.on('timeout', () => {
                    console.error('[TTS:main] Request timeout');
                    req.destroy();
                    resolve({ error: 'TTS request timeout' });
                });
                req.write(postData);
                req.end();
            });
        } catch (e) {
            console.error('[TTS:main] Exception:', e.message);
            return { error: e.message };
        }
    });

    // ── Conversation Threads (Persistence) ────────────────────
    conversationStore = new ConversationStore();
    ipcMain.handle('threads:list', async () => conversationStore.listThreads());
    ipcMain.handle('threads:create', async () => conversationStore.createThread());
    ipcMain.handle('threads:load', async (_, id) => conversationStore.loadThread(id));
    ipcMain.handle('threads:append', async (_, id, msg) => {
        conversationStore.appendMessage(id, msg);
        return { ok: true };
    });
    ipcMain.handle('threads:rename', async (_, id, title) => {
        conversationStore.renameThread(id, title);
        return { ok: true };
    });
    ipcMain.handle('threads:delete', async (_, id) => {
        conversationStore.deleteThread(id);
        return { ok: true };
    });

    // ── Agent (Agentic Loop) ─────────────────────────────────
    ipcMain.handle('agent:status', async () => agent.getStatus());
    ipcMain.handle('agent:tools', async () => agent.getToolSchemas());
    ipcMain.handle('agent:approve', async (_, proposalId, confirmText) => {
        const result = await agent.executeApproved(proposalId, confirmText);
        // v4.2: If the agent continued reasoning after approval, surface it as agentResponse
        if (result.continuation) {
            result.agentResponse = result.continuation;
        }
        return result;
    });
    ipcMain.handle('agent:deny', async (_, proposalId, reason) => {
        return agent.denyProposal(proposalId, reason);
    });
    ipcMain.handle('agent:approve-all', async () => {
        return await agent.executeAllPending();
    });

    // v5.1: Hermes ACP integration — start/stop Hermes channel
    ipcMain.handle('agent:start-hermes', async () => {
        try {
            await agent.startHermes();
            agent._useHermes = true;
            console.log('[OMEGA] Hermes ACP channel started — backend switched to Hermes');
            return { ok: true, mode: 'hermes' };
        } catch (err) {
            console.error('[OMEGA] Failed to start Hermes:', err);
            return { ok: false, error: err.message };
        }
    });
    ipcMain.handle('agent:stop-hermes', async () => {
        try {
            agent._useHermes = false;
            agent.stopHermes();
            console.log('[OMEGA] Hermes ACP channel stopped — backend reverted to Ollama');
            return { ok: true, mode: 'ollama' };
        } catch (err) {
            console.error('[OMEGA] Failed to stop Hermes:', err);
            return { ok: false, error: err.message };
        }
    });

    // ── MCP Health (omega-brain, sswp, omega-stenographer, etc.) ─────
    // Polls Hermes for MCP server status. Called by the renderer to surface
    // health in the UI and at app startup to verify the agent toolset is wired.
    const REQUIRED_MCPS = ['omega-brain', 'sswp', 'omega-stenographer'];

    // Generic MCP stdio caller — reads Hermes config, spawns server, sends JSON-RPC tool call
    async function mcpCall(serverName, toolName, args) {
        const yaml = require('js-yaml');
        const fs = require('fs');
        const hermesConfigPath = path.join(os.homedir(), '.hermes', 'config.yaml');
        if (!fs.existsSync(hermesConfigPath)) throw new Error('Hermes config not found');
        const config = yaml.load(fs.readFileSync(hermesConfigPath, 'utf8'));
        const serverCfg = config?.mcp?.servers?.[serverName] || config?.mcp_servers?.[serverName];
        if (!serverCfg) throw new Error(`MCP server '${serverName}' not found in Hermes config`);

        return new Promise((resolve, reject) => {
            const proc = spawn(serverCfg.command, serverCfg.args || [], {
                env: { ...process.env, ...(serverCfg.env || {}) },
                stdio: ['pipe', 'pipe', 'pipe']
            });
            let stdout = '';
            let buffer = '';
            let state = 'init'; // init -> initialized -> called -> done
            let reqId = 1;

            function send(obj) {
                try { proc.stdin.write(JSON.stringify(obj) + '\n'); } catch (e) { reject(e); }
            }

            proc.stdout.on('data', (d) => {
                buffer += d.toString();
                let nl;
                while ((nl = buffer.indexOf('\n')) !== -1) {
                    const line = buffer.slice(0, nl).trim();
                    buffer = buffer.slice(nl + 1);
                    if (!line) continue;
                    stdout += line + '\n';
                    let msg;
                    try { msg = JSON.parse(line); } catch { continue; }

                    if (state === 'init' && msg.id === 1 && msg.result) {
                        state = 'initialized';
                        send({ jsonrpc: '2.0', method: 'notifications/initialized' });
                        // Now call the tool
                        send({ jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: toolName, arguments: args || {} } });
                        state = 'called';
                    } else if (state === 'called' && msg.id === 2) {
                        state = 'done';
                        proc.kill();
                        if (msg.error) {
                            reject(new Error(msg.error.message || JSON.stringify(msg.error)));
                        } else {
                            resolve(msg.result);
                        }
                    }
                }
            });

            proc.stderr.on('data', (d) => { /* MCP servers often log to stderr — ignore */ });
            proc.on('error', (e) => reject(e));
            proc.on('close', (code) => {
                if (state !== 'done') {
                    reject(new Error(`MCP server exited (code ${code}) before completing call. stdout: ${stdout.substring(0, 500)}`));
                }
            });

            const timer = setTimeout(() => {
                proc.kill();
                reject(new Error('MCP call timeout (15s)'));
            }, 15000);

            proc.on('close', () => clearTimeout(timer));

            // Kick off handshake
            send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'gravity-omega', version: '5.2' } } });
        });
    }

    ipcMain.handle('mcp:call', async (_, { server, tool, args }) => {
        try {
            const result = await mcpCall(server, tool, args);
            return { ok: true, result };
        } catch (e) {
            return { ok: false, error: e.message };
        }
    });
    ipcMain.handle('mcp:status', async () => {
        // Try hermes directly first (WSL/Linux), then fall back to Windows cmd.exe path
        const servers = [];
        let error = null;

        async function tryHermes(args) {
            return new Promise((resolve) => {
                let stdout = '';
                const proc = spawn(args[0], args.slice(1), { stdio: ['ignore', 'pipe', 'pipe'] });
                const timer = setTimeout(() => { proc.kill(); resolve({ timeout: true }); }, 6000);
                proc.stdout.on('data', d => stdout += d.toString());
                proc.stderr.on('data', d => stdout += d.toString());
                proc.on('close', () => { clearTimeout(timer); resolve({ stdout }); });
                proc.on('error', () => { clearTimeout(timer); resolve({ error: true }); });
            });
        }

        // Path 1: hermes available directly (WSL/Linux/Mac)
        let result = await tryHermes(['hermes', 'mcp', 'list']);
        // Path 2: via cmd.exe -> wsl (Windows host running Electron)
        if (!result.stdout || result.error || result.timeout) {
            result = await tryHermes(['cmd.exe', '/c', 'wsl', 'bash', '-lc', 'hermes mcp list 2>&1']);
        }

        if (result.stdout) {
            for (const line of result.stdout.split(/\r?\n/)) {
                const m = line.match(/^\s*([a-z][a-z0-9_-]*)\s+\S.*?(✓ enabled|✗ disabled|✗ \w+)/i);
                if (m) servers.push({ name: m[1], status: m[2].includes('✓') ? 'enabled' : 'disabled' });
            }
        } else {
            error = result.timeout ? 'timeout' : 'hermes unavailable';
        }

        const required = REQUIRED_MCPS.map(name => {
            const found = servers.find(s => s.name === name);
            return { name, present: !!found, status: found ? found.status : 'missing' };
        });

        // If hermes list failed but the local MCP server is listening, at least mark the IDE server ok
        if (error && !servers.length) {
            try {
                const http = require('http');
                await new Promise((res) => {
                    const req = http.get('http://127.0.0.1:3002/health', (r) => {
                        if (r.statusCode === 200) servers.push({ name: 'gravity-omega-ide', status: 'enabled' });
                        res();
                    }).on('error', () => res());
                    setTimeout(() => res(), 1000);
                });
            } catch { /* ignore */ }
        }

        return { servers, required, allRequiredOk: required.every(r => r.status === 'enabled'), error };
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

        // GPU/VRAM via nvidia-smi (non-blocking best-effort, spawn so no shell injection)
        try {
            const nvOut = await new Promise((resolve, reject) => {
                let out = '';
                const proc = spawn('nvidia-smi', ['--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], { stdio: ['ignore', 'pipe', 'pipe'] });
                const timer = setTimeout(() => { proc.kill(); reject(new Error('timeout')); }, 3000);
                proc.stdout.on('data', d => out += d);
                proc.on('close', (code) => { clearTimeout(timer); code === 0 ? resolve(out) : reject(new Error(`exit ${code}`)); });
                proc.on('error', (e) => { clearTimeout(timer); reject(e); });
            });
            const parts = nvOut.trim().split(',').map(s => s.trim());
            if (parts.length >= 5) {
                const [vTotal, vUsed, vFree, util] = parts.slice(1, 5).map(n => parseInt(n, 10));
                info.gpu = {
                    name: String(parts[0]).substring(0, 100),
                    vram_total_mb: Number.isFinite(vTotal) ? vTotal : null,
                    vram_used_mb:  Number.isFinite(vUsed)  ? vUsed  : null,
                    vram_free_mb:  Number.isFinite(vFree)  ? vFree  : null,
                    utilization:   Number.isFinite(util)   ? util   : null,
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

    // ── OCR Handlers ─────────────────────────────────────────────
    ipcMain.handle('ocr:extract-text', async (_, imageData, filename) => {
        try {
            const text = await ocrHandler.extractTextFromBuffer(imageData, filename);
            return { success: true, text };
        } catch (error) {
            console.error('[OCR] Extraction failed:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('ocr:terminate', async () => {
        try {
            await ocrHandler.terminate();
            return { success: true };
        } catch (error) {
            console.error('[OCR] Termination failed:', error);
            return { success: false, error: error.message };
        }
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
                    const finishReason = parsed.candidates?.[0]?.finishReason;
                    const blockReason = parsed.promptFeedback?.blockReason;
                    if (content) resolve(content);
                    else if (blockReason) reject(new Error(`Gemini safety block: ${blockReason}`));
                    else if (parsed.error) reject(new Error(parsed.error.message));
                    else reject(new Error(`Gemini empty response (finishReason=${finishReason || 'unknown'})`));
                } catch (e) { reject(new Error(`Gemini decode error: ${e.message}`)); }
            });
        });
        req.on('error', reject);
        req.on('timeout', () => { req.destroy(); reject(new Error('Gemini timeout')); });
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

    // Guard: only register IPC handlers once to prevent duplicate listeners
    if (!ipcRegistered) {
        registerIPC();
        ipcRegistered = true;
    }
    buildMenu();
    createWindow();

    // ── MCP Server — expose all IDE tools on port 3002 ────────
    try {
        let ptyMod = null;
        try { ptyMod = require('node-pty'); } catch {}
        startMcpServer({
            getWindow: () => mainWindow,
            terminals,
            browser,
            bridge,
            agent,
            ptyModule: ptyMod,
            terminalCounter: { value: terminalCounter },
        });
        console.log('[Omega] MCP server started — Hermes can connect on port 3002');
    } catch (mcpErr) {
        console.error('[Omega] MCP server failed to start:', mcpErr.message);
    }

    // ── Media Player: Global play/pause shortcut ─────────────
    try {
        globalShortcut.register('MediaPlayPause', () => {
            mainWindow?.webContents.send('omega:media-toggle');
        });
        // Fallback for keyboards without media keys
        globalShortcut.register('Ctrl+Shift+Space', () => {
            mainWindow?.webContents.send('omega:media-toggle');
        });
    } catch (e) { console.warn('[Omega] Media shortcuts failed:', e.message); }

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

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});

// ── Graceful Shutdown ────────────────────────────────────────
// Electron does not await async before-quit handlers — the process
// exits before the work finishes. Pattern below: preventDefault on the
// first invocation, run all async cleanup with a hard timeout, then
// re-call app.quit() with _shuttingDown set so we don't loop.

let _shuttingDown = false;

async function gracefulShutdown(reason) {
    crashLog(`gracefulShutdown(${reason}) starting`);
    console.log(`[Omega] Graceful shutdown: ${reason}`);
    context.addBreadcrumb('lifecycle', `Shutting down: ${reason}`);

    // Hard 5s budget for all async cleanup — if any step hangs we still exit.
    const deadline = setTimeout(() => {
        crashLog('gracefulShutdown deadline exceeded — forcing exit');
        console.error('[Omega] Shutdown deadline exceeded — forcing exit');
        process.exit(1);
    }, 5000);

    try {
        await Promise.allSettled([
            hooks.fire('on_shutdown'),
            (async () => { if (watcher) { try { await watcher.close(); } catch {} watcher = null; } })(),
            (async () => {
                for (const [, term] of terminals) {
                    try { term.removeAllListeners(); term.kill(); } catch {}
                }
                terminals.clear();
            })(),
            (async () => { try { await browser.close(); } catch {} })(),
            (async () => { try { await bridge.stop(); } catch {} })(),
            (async () => { try { await context.close(); } catch {} })(),
            (async () => { try { agent.gate.dispose(); } catch {} })(),
        ]);
        crashLog('gracefulShutdown cleanup complete');
    } finally {
        clearTimeout(deadline);
    }
}

app.on('before-quit', (event) => {
    if (_shuttingDown) return;             // second pass: let it actually quit
    _shuttingDown = true;
    event.preventDefault();
    crashLog('before-quit fired (deferring for async cleanup)');
    gracefulShutdown('before-quit').finally(() => {
        crashLog('cleanup done — calling app.quit()');
        app.quit();
    });
});

process.on('exit', (code) => {
    crashLog(`process.exit code=${code}`);
    console.log(`[Omega] Process exit with code: ${code}`);
});

process.on('beforeExit', (code) => {
    crashLog(`process.beforeExit code=${code}`);
    console.log(`[Omega] beforeExit with code: ${code}`);
});

// SIGTERM/SIGINT → trigger graceful shutdown via app.quit() so before-quit fires.
function _handleSignal(sig) {
    crashLog(`${sig} received`);
    console.log(`[Omega] ${sig} received — initiating graceful shutdown`);
    if (_shuttingDown) return;
    // app.quit() will fire before-quit which runs gracefulShutdown
    app.quit();
}
process.on('SIGTERM', () => _handleSignal('SIGTERM'));
process.on('SIGINT',  () => _handleSignal('SIGINT'));
if (process.platform === 'win32') {
    // SIGBREAK fires on Ctrl+Break in Windows consoles
    process.on('SIGBREAK', () => _handleSignal('SIGBREAK'));
}
