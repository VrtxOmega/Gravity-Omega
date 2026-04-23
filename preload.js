/**
 * GRAVITY OMEGA v2.0 — Preload Script
 * Secure bridge between Main and Renderer via contextBridge.
 * Every namespace here maps 1:1 to an IPC handler in main.js.
 */
const { contextBridge, ipcRenderer } = require('electron');

// v4.2: Module-level wrapper map for correct on/removeListener pairing
const _ipcWrappers = new Map();

contextBridge.exposeInMainWorld('omega', {
    // ── File Operations ──────────────────────────────────────
    file: {
        read:       (p) => ipcRenderer.invoke('file:read', p),
        save:       (p, c) => ipcRenderer.invoke('file:save', p, c),
        listDir:    (p) => ipcRenderer.invoke('file:listDir', p),
        openDialog: () => ipcRenderer.invoke('file:openDialog'),
        openFolder: () => ipcRenderer.invoke('file:openFolder'),
        saveDialog: (n) => ipcRenderer.invoke('file:saveDialog', n),
        exists:     (p) => ipcRenderer.invoke('file:exists', p),
        mkdir:      (p) => ipcRenderer.invoke('file:mkdir', p),
        delete:     (p, r) => ipcRenderer.invoke('file:delete', p, r),
        rename:     (o, n) => ipcRenderer.invoke('file:rename', o, n),
        openAudioFolder: () => ipcRenderer.invoke('media:openAudioFolder'),
        saveMediaState: (state) => ipcRenderer.invoke('media:saveState', state),
        loadMediaState: () => ipcRenderer.invoke('media:loadState'),
        importToLibrary: (srcPath) => ipcRenderer.invoke('media:importToLibrary', srcPath),
        scanFolder: (folderPath) => ipcRenderer.invoke('media:scanFolder', folderPath),
        getMetadata: (filePath) => ipcRenderer.invoke('media:getMetadata', filePath),
        getCoverArt: (filePath) => ipcRenderer.invoke('media:getCoverArt', filePath),
        decryptAAX: (filePath) => ipcRenderer.invoke('media:decryptAAX', filePath),
    },

    // ── Terminal (PTY) ───────────────────────────────────────
    terminal: {
        create:   () => ipcRenderer.invoke('terminal:create'),
        write:    (id, data) => ipcRenderer.send('terminal:input', id, data),
        resize:   (id, cols, rows) => ipcRenderer.send('terminal:resize', id, cols, rows),
        kill:     (id) => ipcRenderer.send('terminal:kill', id),
        onData:   (cb) => ipcRenderer.on('terminal:data', (_, id, data) => cb(id, data)),
        onExit:   (cb) => ipcRenderer.on('terminal:exit', (_, id, code) => cb(id, code)),
    },

    // ── File Watcher ─────────────────────────────────────────
    watcher: {
        start:   (p) => ipcRenderer.invoke('watcher:start', p),
        onEvent: (cb) => ipcRenderer.on('watcher:event', (_, type, path) => cb(type, path)),
    },

    // ── Search ───────────────────────────────────────────────
    search: {
        text: (dir, query) => ipcRenderer.invoke('search:text', dir, query),
    },

    // ── Backend Bridge ───────────────────────────────────────
    status:   () => ipcRenderer.invoke('backend:status'),
    modules:  () => ipcRenderer.invoke('backend:modules'),
    execute:  (id, args) => ipcRenderer.invoke('backend:execute', id, args),
    describe: (id) => ipcRenderer.invoke('backend:describe', id),

    // ── Chat (Agentic) ───────────────────────────────────────
    chat: {
        send:  (text, sessionId, model) => ipcRenderer.invoke('chat:send', text, sessionId, model),
        abort: (sessionId) => ipcRenderer.invoke('chat:abort', sessionId),
        tts:   (text) => ipcRenderer.invoke('chat:tts', text),
    },

    // ── Conversation Threads (Persistence) ───────────────────
    threads: {
        list:   ()          => ipcRenderer.invoke('threads:list'),
        create: ()          => ipcRenderer.invoke('threads:create'),
        load:   (id)        => ipcRenderer.invoke('threads:load', id),
        append: (id, msg)   => ipcRenderer.invoke('threads:append', id, msg),
        rename: (id, title) => ipcRenderer.invoke('threads:rename', id, title),
        delete: (id)        => ipcRenderer.invoke('threads:delete', id),
    },

    // ── Agent (Agentic Loop) ─────────────────────────────────
    agent: {
        status:     () => ipcRenderer.invoke('agent:status'),
        tools:      () => ipcRenderer.invoke('agent:tools'),
        approve:    (id, text) => ipcRenderer.invoke('agent:approve', id, text),
        deny:       (id, reason) => ipcRenderer.invoke('agent:deny', id, reason),
        approveAll: () => ipcRenderer.invoke('agent:approve-all'),
        // v5.1: Hermes ACP integration — start/stop Hermes channel and toggle backend
        startHermes: () => ipcRenderer.invoke('agent:start-hermes'),
        stopHermes:  () => ipcRenderer.invoke('agent:stop-hermes'),
    },

    // ── Hardware ─────────────────────────────────────────────
    hardware: () => ipcRenderer.invoke('hardware:info'),

    // ── Browser Automation ───────────────────────────────────
    browser: {
        navigate:   (url) => ipcRenderer.invoke('browser:navigate', url),
        screenshot: (name) => ipcRenderer.invoke('browser:screenshot', name),
        task:       (steps) => ipcRenderer.invoke('browser:task', steps),
        close:      () => ipcRenderer.invoke('browser:close'),
    },

    // ── Reports (EasyStreet Pipeline) ────────────────────────
    reports: {
        drafts:    () => ipcRenderer.invoke('reports:drafts'),
        targets:   () => ipcRenderer.invoke('reports:targets'),
        rainmaker: () => ipcRenderer.invoke('reports:rainmaker'),
        pipeline:  () => ipcRenderer.invoke('reports:pipeline'),
    },

    // ── Security Panel ───────────────────────────────────────
    security: {
        scan:          () => ipcRenderer.invoke('security:scan'),
        gravityShield: (a) => ipcRenderer.invoke('security:gravity-shield', a),
        void:          (a) => ipcRenderer.invoke('security:void', a),
        basilisk:      (a) => ipcRenderer.invoke('security:basilisk', a),
        nemesis:       (a) => ipcRenderer.invoke('security:nemesis', a),
        containment:   () => ipcRenderer.invoke('security:containment'),
        processes:     () => ipcRenderer.invoke('security:processes'),
        ports:         () => ipcRenderer.invoke('security:ports'),
        fullScan:      () => ipcRenderer.invoke('security:full-scan'),
        destroy:       () => ipcRenderer.invoke('security:destroy'),
    },

    // ── Tools (Operations) ───────────────────────────────────
    tools: {
        credits:    () => ipcRenderer.invoke('tools:credits'),
        brain:      () => ipcRenderer.invoke('tools:brain'),
        vision:     () => ipcRenderer.invoke('tools:vision'),
        alerts:     () => ipcRenderer.invoke('tools:alerts'),
        sendEmail:  (d) => ipcRenderer.invoke('tools:send-email', d),
        codeReview: (d) => ipcRenderer.invoke('tools:code-review', d),
        autoAudit:  (d) => ipcRenderer.invoke('tools:auto-audit', d),
    },

    // ── Ledger ───────────────────────────────────────────────
    ledger: {
        stats:  () => ipcRenderer.invoke('ledger:stats'),
        search: (q) => ipcRenderer.invoke('ledger:search', q),
    },

    // ── Vault (Veritas Vault + Mnemo-Cortex) ─────────────────
    vault: {
        search:     (q) => ipcRenderer.invoke('vault:search', q),
        getContext:  () => ipcRenderer.invoke('vault:context'),
        getSessions: () => ipcRenderer.invoke('vault:sessions'),
        getKIHealth: () => ipcRenderer.invoke('vault:ki-health'),
        sweep:       () => ipcRenderer.invoke('vault:sweep'),
    },

    // ── Window Controls ──────────────────────────────────────
    window: {
        minimize: () => ipcRenderer.send('window:minimize'),
        maximize: () => ipcRenderer.send('window:maximize'),
        close:    () => ipcRenderer.send('window:close'),
    },

    // ── Event Bus (Main → Renderer) ──────────────────────────
    // v4.2 fix: Track wrapper→original mapping so removeListener works correctly.
    on: (channel, cb) => {
        const allowed = [
            'menu:open-file', 'menu:open-folder', 'menu:save',
            'menu:new-terminal', 'omega:bridge-status-change',
            'omega:backend-ready', 'omega:agent-action',
            'omega:agent-step', 'omega:agent-complete',
            'omega:sentinel-alert', 'omega:open-file',
            'omega:media-toggle',
        ];
        if (allowed.includes(channel)) {
            const wrapper = (_, ...args) => cb(...args);
            _ipcWrappers.set(cb, wrapper);
            ipcRenderer.on(channel, wrapper);
        }
    },
    removeListener: (channel, cb) => {
        const wrapper = _ipcWrappers.get(cb);
        if (wrapper) {
            ipcRenderer.removeListener(channel, wrapper);
            _ipcWrappers.delete(cb);
        } else {
            ipcRenderer.removeListener(channel, cb);
        }
    },
});
