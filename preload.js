/**
 * GRAVITY OMEGA v3.0 â€” Preload Script
 * Secure bridge between Main and Renderer via contextBridge.
 * Every namespace here maps 1:1 to an IPC handler in main.js.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('omega', {
    // â”€â”€ File Operations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    // â”€â”€ Terminal (PTY) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    terminal: {
        create:   () => ipcRenderer.invoke('terminal:create'),
        write:    (id, data) => ipcRenderer.send('terminal:input', id, data),
        resize:   (id, cols, rows) => ipcRenderer.send('terminal:resize', id, cols, rows),
        kill:     (id) => ipcRenderer.send('terminal:kill', id),
        onData:   (cb) => ipcRenderer.on('terminal:data', (_, id, data) => cb(id, data)),
        onExit:   (cb) => ipcRenderer.on('terminal:exit', (_, id, code) => cb(id, code)),
    },

    // â”€â”€ File Watcher â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    watcher: {
        start:   (p) => ipcRenderer.invoke('watcher:start', p),
        onEvent: (cb) => ipcRenderer.on('watcher:event', (_, type, path) => cb(type, path)),
    },

    // â”€â”€ Search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    search: {
        text: (dir, query) => ipcRenderer.invoke('search:text', dir, query),
    },

    // â”€â”€ Backend Bridge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    status:   () => ipcRenderer.invoke('backend:status'),
    modules:  () => ipcRenderer.invoke('backend:modules'),
    execute:  (id, args) => ipcRenderer.invoke('backend:execute', id, args),
    describe: (id) => ipcRenderer.invoke('backend:describe', id),

    // â”€â”€ Chat (Agentic) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    chat: {
        send:  (text, sessionId) => ipcRenderer.invoke('chat:send', text, sessionId),
        abort: (sessionId) => ipcRenderer.invoke('chat:abort', sessionId),
        tts:   (text) => ipcRenderer.invoke('chat:tts', text),
    },

    // â”€â”€ Agent (Agentic Loop) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    agent: {
        status:     () => ipcRenderer.invoke('agent:status'),
        tools:      () => ipcRenderer.invoke('agent:tools'),
        approve:    (id, text) => ipcRenderer.invoke('agent:approve', id, text),
        deny:       (id, reason) => ipcRenderer.invoke('agent:deny', id, reason),
        approveAll: () => ipcRenderer.invoke('agent:approve-all'),
    },

    // â”€â”€ Hardware â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    hardware: () => ipcRenderer.invoke('hardware:info'),

    // â”€â”€ Browser Automation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    browser: {
        navigate:   (url) => ipcRenderer.invoke('browser:navigate', url),
        screenshot: (name) => ipcRenderer.invoke('browser:screenshot', name),
        task:       (steps) => ipcRenderer.invoke('browser:task', steps),
        close:      () => ipcRenderer.invoke('browser:close'),
    },

    // â”€â”€ Reports (EasyStreet Pipeline) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    reports: {
        drafts:    () => ipcRenderer.invoke('reports:drafts'),
        targets:   () => ipcRenderer.invoke('reports:targets'),
        rainmaker: () => ipcRenderer.invoke('reports:rainmaker'),
        pipeline:  () => ipcRenderer.invoke('reports:pipeline'),
    },

    // â”€â”€ Security Panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    // â”€â”€ Tools (Operations) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tools: {
        credits:    () => ipcRenderer.invoke('tools:credits'),
        brain:      () => ipcRenderer.invoke('tools:brain'),
        vision:     () => ipcRenderer.invoke('tools:vision'),
        alerts:     () => ipcRenderer.invoke('tools:alerts'),
        sendEmail:  (d) => ipcRenderer.invoke('tools:send-email', d),
        codeReview: (d) => ipcRenderer.invoke('tools:code-review', d),
        autoAudit:  (d) => ipcRenderer.invoke('tools:auto-audit', d),
    },

    // â”€â”€ Ledger â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ledger: {
        stats:  () => ipcRenderer.invoke('ledger:stats'),
        search: (q) => ipcRenderer.invoke('ledger:search', q),
    },

    // â”€â”€ Vault (Veritas Vault + Mnemo-Cortex) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    vault: {
        search:     (q) => ipcRenderer.invoke('vault:search', q),
        getContext:  () => ipcRenderer.invoke('vault:context'),
        getSessions: () => ipcRenderer.invoke('vault:sessions'),
        getKIHealth: () => ipcRenderer.invoke('vault:ki-health'),
        sweep:       () => ipcRenderer.invoke('vault:sweep'),
    },

    // â”€â”€ Window Controls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    window: {
        minimize: () => ipcRenderer.send('window:minimize'),
        maximize: () => ipcRenderer.send('window:maximize'),
        close:    () => ipcRenderer.send('window:close'),
    },

    // â”€â”€ Event Bus (Main â†’ Renderer) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
