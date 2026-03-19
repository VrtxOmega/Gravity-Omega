/**
 * GRAVITY OMEGA v2.0 — Preload Script
 * Secure bridge between Main and Renderer via contextBridge.
 * Every namespace here maps 1:1 to an IPC handler in main.js.
 */
const { contextBridge, ipcRenderer } = require('electron');

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
        send:  (text, sessionId) => ipcRenderer.invoke('chat:send', text, sessionId),
        abort: (sessionId) => ipcRenderer.invoke('chat:abort', sessionId),
        tts:   (text) => ipcRenderer.invoke('chat:tts', text),
    },

    // ── Agent (Agentic Loop) ─────────────────────────────────
    agent: {
        status:     () => ipcRenderer.invoke('agent:status'),
        tools:      () => ipcRenderer.invoke('agent:tools'),
        approve:    (id, text) => ipcRenderer.invoke('agent:approve', id, text),
        deny:       (id, reason) => ipcRenderer.invoke('agent:deny', id, reason),
        approveAll: () => ipcRenderer.invoke('agent:approve-all'),
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
    on: (channel, cb) => {
        const allowed = [
            'menu:open-file', 'menu:open-folder', 'menu:save',
            'menu:new-terminal', 'omega:bridge-status-change',
            'omega:backend-ready', 'omega:agent-action',
            'omega:agent-step', 'omega:agent-complete',
            'omega:sentinel-alert',
        ];
        if (allowed.includes(channel)) {
            ipcRenderer.on(channel, (_, ...args) => cb(...args));
        }
    },
    removeListener: (channel, cb) => {
        ipcRenderer.removeListener(channel, cb);
    },
});
