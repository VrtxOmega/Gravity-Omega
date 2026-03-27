/**
 * GRAVITY OMEGA v3.0 — Renderer Application
 *
 * Orchestrates the entire UI:
 *   - Monaco Editor (omega-dark theme)
 *   - xterm.js Terminal Manager
 *   - File Explorer with chokidar live-watch
 *   - Activity Bar panel switching
 *   - Chat system (agentic streaming)
 *   - Vault panel (FTS5 search, KI health, sessions)
 *   - Module cards, Reports, Security, Tools, Ledger
 *   - Toast notifications, resize handles, keyboard shortcuts
 *
 * Every UI action routes through window.omega (preload.js bridge).
 */
'use strict';

// ══════════════════════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════════════════════

const state = {
    openFiles: new Map(),   // path → { content, model, viewState, dirty }
    activeFile: null,
    workspaceDir: null,
    activePanel: 'explorer',
    terminal: {
        instances: new Map(),  // id → { terminal, fitAddon }
        activeId: null,
        counter: 0,
    },
    chat: { sessionId: crypto.randomUUID(), history: [], sending: false },
    editor: null,
    toasts: [],
};

// ══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════

function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ══════════════════════════════════════════════════════════════
// MONACO EDITOR SETUP
// ══════════════════════════════════════════════════════════════

function initMonaco() {
    // Register Omega Dark theme
    monaco.editor.defineTheme('omega-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'comment', foreground: '666666', fontStyle: 'italic' },
            { token: 'keyword', foreground: 'd4a843' },
            { token: 'string', foreground: 'a8d080' },
            { token: 'number', foreground: 'e0a040' },
            { token: 'type', foreground: '50d0d0' },
            { token: 'function', foreground: '60a0e0' },
            { token: 'variable', foreground: 'e0e0e0' },
            { token: 'operator', foreground: 'c0c0c0' },
            { token: 'delimiter', foreground: '888888' },
            { token: 'tag', foreground: 'd4a843' },
            { token: 'attribute.name', foreground: '50d0d0' },
            { token: 'attribute.value', foreground: 'a8d080' },
        ],
        colors: {
            'editor.background': '#0e0e0e',
            'editor.foreground': '#e0e0e0',
            'editor.lineHighlightBackground': '#1a1a1a',
            'editor.selectionBackground': '#d4a84330',
            'editor.selectionHighlightBackground': '#d4a84315',
            'editorCursor.foreground': '#d4a843',
            'editorLineNumber.foreground': '#444444',
            'editorLineNumber.activeForeground': '#d4a843',
            'editorIndentGuide.background': '#1e1e1e',
            'editorIndentGuide.activeBackground': '#333333',
            'editorBracketMatch.background': '#d4a84320',
            'editorBracketMatch.border': '#d4a84350',
            'editor.findMatchBackground': '#d4a84340',
            'editor.findMatchHighlightBackground': '#d4a84320',
        },
    });

    state.editor = monaco.editor.create(document.getElementById('monaco-container'), {
        value: '',
        language: 'plaintext',
        theme: 'omega-dark',
        fontFamily: "'JetBrains Mono', 'Consolas', monospace",
        fontSize: 13,
        lineHeight: 20,
        minimap: { enabled: true, maxColumn: 80 },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        formatOnPaste: true,
        suggestOnTriggerCharacters: true,
        bracketPairColorization: { enabled: true },
        smoothScrolling: true,
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
        padding: { top: 8 },
        renderWhitespace: 'selection',
    });

    // Track cursor position in status bar
    state.editor.onDidChangeCursorPosition((e) => {
        document.getElementById('status-position').textContent =
            `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
    });

    // Track dirty state
    state.editor.onDidChangeModelContent(() => {
        if (state.activeFile) {
            const file = state.openFiles.get(state.activeFile);
            if (file) file.dirty = true;
            updateTabDirty(state.activeFile, true);
        }
    });
}

// ══════════════════════════════════════════════════════════════
// FILE OPERATIONS
// ══════════════════════════════════════════════════════════════

function detectLanguage(filePath) {
    const ext = filePath.split('.').pop().toLowerCase();
    const map = {
        js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
        py: 'python', html: 'html', css: 'css', json: 'json', md: 'markdown',
        sol: 'sol', rs: 'rust', go: 'go', java: 'java', c: 'c', cpp: 'cpp',
        h: 'c', sh: 'shell', bash: 'shell', yaml: 'yaml', yml: 'yaml',
        xml: 'xml', sql: 'sql', toml: 'ini', cfg: 'ini', env: 'ini',
    };
    return map[ext] || 'plaintext';
}

async function openFile(filePath) {
    // If already open, just switch to it
    if (state.openFiles.has(filePath)) {
        switchToFile(filePath);
        return;
    }

    const result = await window.omega.file.read(filePath);
    if (result.error) {
        // v4.3.2: Suppress ENOENT from agent auto-opens (file may not exist yet)
        if (result.error.includes('ENOENT')) {
            console.warn(`[MONACO] File not found (may be pending write): ${filePath}`);
        } else {
            showToast(`Error opening file: ${result.error}`, 'error');
        }
        return;
    }

    const lang = detectLanguage(filePath);
    const ext = filePath.split('.').pop().toLowerCase();
    const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'].includes(ext);

    const model = isImage ? null : monaco.editor.createModel(result.content, lang);

    state.openFiles.set(filePath, {
        content: result.content, model, dirty: false,
        name: result.name, lang, isImage,
    });

    addTab(filePath, result.name);
    switchToFile(filePath);
    document.getElementById('status-language').textContent = lang;

    // Update titlebar
    document.getElementById('titlebar-filepath').textContent = filePath;
}

function switchToFile(filePath) {
    const file = state.openFiles.get(filePath);
    if (!file) return;

    // Save current view state
    if (state.activeFile && state.openFiles.has(state.activeFile)) {
        const current = state.openFiles.get(state.activeFile);
        if (current.model && state.editor) {
            current.viewState = state.editor.saveViewState();
        }
    }

    state.activeFile = filePath;

    const monacoEl = document.getElementById('monaco-container');
    const welcomeEl = document.getElementById('welcome-screen');
    const jsonEl = document.getElementById('json-viewer');
    const mdEl = document.getElementById('markdown-viewer');
    const imgEl = document.getElementById('image-viewer');

    // Hide all viewers
    [monacoEl, welcomeEl, jsonEl, mdEl, imgEl].forEach(el => el.classList.add('hidden'));

    if (file.isImage) {
        imgEl.classList.remove('hidden');
        document.getElementById('image-viewer-img').src = `omega-file://${filePath}`;
    } else if (file.lang === 'json') {
        monacoEl.classList.remove('hidden');
        state.editor.setModel(file.model);
        if (file.viewState) state.editor.restoreViewState(file.viewState);
    } else if (file.lang === 'markdown') {
        monacoEl.classList.remove('hidden');
        state.editor.setModel(file.model);
        if (file.viewState) state.editor.restoreViewState(file.viewState);
    } else {
        monacoEl.classList.remove('hidden');
        state.editor.setModel(file.model);
        if (file.viewState) state.editor.restoreViewState(file.viewState);
    }

    // Monaco needs layout() after its container becomes visible
    requestAnimationFrame(() => state.editor.layout());
    state.editor.focus();
    updateActiveTab(filePath);
    document.getElementById('status-language').textContent = file.lang || 'Plain Text';
    document.getElementById('titlebar-filepath').textContent = filePath;
}

async function saveFile(filePath) {
    const file = state.openFiles.get(filePath || state.activeFile);
    const path = filePath || state.activeFile;
    if (!file || !path) return;

    const content = file.model ? file.model.getValue() : file.content;
    const result = await window.omega.file.save(path, content);
    if (result.error) {
        showToast(`Save failed: ${result.error}`, 'error');
        return;
    }
    file.dirty = false;
    file.content = content;
    updateTabDirty(path, false);
    showToast(`Saved: ${file.name}`, 'success', 2000);
}

// ══════════════════════════════════════════════════════════════
// TAB MANAGEMENT
// ══════════════════════════════════════════════════════════════

function addTab(filePath, name) {
    const tabsEl = document.getElementById('editor-tabs');
    const tab = document.createElement('div');
    tab.className = 'tab';
    tab.dataset.tab = filePath;
    tab.innerHTML = `<span class="tab-name">${name}</span><span class="tab-close" title="Close">×</span>`;
    tab.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-close')) {
            closeTab(filePath);
            return;
        }
        switchToFile(filePath);
    });
    tabsEl.appendChild(tab);
}

function updateActiveTab(filePath) {
    document.querySelectorAll('#editor-tabs .tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === filePath);
    });
}

function updateTabDirty(filePath, dirty) {
    const tab = document.querySelector(`#editor-tabs .tab[data-tab="${CSS.escape(filePath)}"]`);
    if (!tab) return;
    const name = tab.querySelector('.tab-name');
    if (name && !name.textContent.endsWith(' ●') && dirty) {
        name.textContent += ' ●';
    } else if (name && name.textContent.endsWith(' ●') && !dirty) {
        name.textContent = name.textContent.replace(' ●', '');
    }
}

function closeTab(filePath) {
    const file = state.openFiles.get(filePath);
    if (file?.model) file.model.dispose();
    state.openFiles.delete(filePath);

    const tab = document.querySelector(`#editor-tabs .tab[data-tab="${CSS.escape(filePath)}"]`);
    if (tab) tab.remove();

    if (state.activeFile === filePath) {
        const remaining = [...state.openFiles.keys()];
        if (remaining.length > 0) {
            switchToFile(remaining[remaining.length - 1]);
        } else {
            state.activeFile = null;
            document.getElementById('monaco-container').classList.add('hidden');
            document.getElementById('welcome-screen').classList.remove('hidden');
            document.getElementById('titlebar-filepath').textContent = '';
        }
    }
}

// ══════════════════════════════════════════════════════════════
// FILE EXPLORER
// ══════════════════════════════════════════════════════════════

async function loadFileTree(dirPath) {
    const treeEl = document.getElementById('file-tree');
    treeEl.innerHTML = '';
    state.workspaceDir = dirPath;

    const entries = await window.omega.file.listDir(dirPath);
    if (!Array.isArray(entries)) return;

    for (const entry of entries) {
        const el = createFileEntry(entry, 0);
        treeEl.appendChild(el);
    }

    // Start file watcher
    await window.omega.watcher.start(dirPath);

    showToast(`Opened: ${dirPath.split('/').pop() || dirPath}`, 'info', 2000);
}

function createFileEntry(entry, depth) {
    const el = document.createElement('div');
    el.className = 'file-entry';
    el.style.paddingLeft = `${12 + depth * 16}px`;

    const icon = entry.isDirectory ? '📁' : getFileIcon(entry.name);
    el.innerHTML = `<span class="file-icon">${icon}</span><span class="file-name">${entry.name}</span>`;

    if (entry.isDirectory) {
        el.dataset.dir = entry.path;
        el.dataset.expanded = 'false';
        el.addEventListener('click', async () => {
            if (el.dataset.expanded === 'true') {
                // Collapse
                el.dataset.expanded = 'false';
                const children = el.parentElement.querySelectorAll(`[data-parent="${CSS.escape(entry.path)}"]`);
                children.forEach(c => c.remove());
                el.querySelector('.file-icon').textContent = '📁';
            } else {
                // Expand
                el.dataset.expanded = 'true';
                el.querySelector('.file-icon').textContent = '📂';
                const children = await window.omega.file.listDir(entry.path);
                if (Array.isArray(children)) {
                    for (const child of children) {
                        const childEl = createFileEntry(child, depth + 1);
                        childEl.dataset.parent = entry.path;
                        el.after(childEl);
                    }
                }
            }
        });
    } else {
        el.addEventListener('click', () => openFile(entry.path));
    }

    return el;
}

function getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    const icons = {
        js: '📜', ts: '📘', py: '🐍', json: '📋', html: '🌐', css: '🎨',
        md: '📝', sol: '⧫', rs: '🦀', go: '💎', java: '☕', c: '⚙️',
        sh: '🖥️', yaml: '📄', yml: '📄', png: '🖼️', jpg: '🖼️', gif: '🖼️',
        svg: '🎭', pdf: '📕', zip: '📦', gz: '📦',
    };
    return icons[ext] || '📄';
}

// ══════════════════════════════════════════════════════════════
// TERMINAL MANAGER
// ══════════════════════════════════════════════════════════════

// xterm is loaded via <script> tags in index.html — use globals

async function createTerminal() {
    if (typeof Terminal === 'undefined') {
        showToast('xterm.js not loaded — check script tags', 'error');
        return;
    }
    const result = await window.omega.terminal.create();
    if (result.error) {
        showToast(`Terminal error: ${result.error}`, 'error');
        return;
    }

    const id = result.id;
    state.terminal.counter++;
    const label = `Terminal ${state.terminal.counter}`;

    const terminal = new Terminal({
        fontFamily: "'JetBrains Mono', 'Consolas', monospace",
        fontSize: 13, lineHeight: 1.2,
        theme: {
            background: '#0a0a0a', foreground: '#e0e0e0',
            cursor: '#d4a843', cursorAccent: '#0a0a0a',
            selection: '#d4a84330',
            black: '#1a1a1a', red: '#e06060', green: '#60c060', yellow: '#d4a843',
            blue: '#60a0e0', magenta: '#b060d0', cyan: '#50d0d0', white: '#e0e0e0',
        },
        allowProposedApi: true,
        cursorBlink: true,
    });

    const fitAddon = new FitAddon.FitAddon();
    terminal.loadAddon(fitAddon);

    state.terminal.instances.set(id, { terminal, fitAddon, label, pid: result.pid });

    // ★ Forward keyboard input from xterm → PTY (THIS IS CRITICAL)
    terminal.onData((data) => {
        window.omega.terminal.write(id, data);
    });

    // ★ Forward resize events so PTY matches terminal dimensions
    terminal.onResize(({ cols, rows }) => {
        window.omega.terminal.resize(id, cols, rows);
    });

    // Add terminal tab
    const tabsList = document.getElementById('terminal-tabs-list');
    const tabEl = document.createElement('button');
    tabEl.className = 'terminal-tab active';
    tabEl.dataset.termId = id;
    tabEl.textContent = label;
    tabEl.addEventListener('click', () => switchTerminal(id));
    tabsList.appendChild(tabEl);

    switchTerminal(id);
    showToast(`${label} opened`, 'info', 1500);
}

function switchTerminal(id) {
    const info = state.terminal.instances.get(id);
    if (!info) return;

    state.terminal.activeId = id;

    // Update tabs
    document.querySelectorAll('.terminal-tab').forEach(t =>
        t.classList.toggle('active', t.dataset.termId === id)
    );

    // Attach terminal to container
    const container = document.getElementById('terminal-container');
    container.innerHTML = '';
    info.terminal.open(container);
    setTimeout(() => {
        info.fitAddon.fit();
        info.terminal.focus();
    }, 50);
}

// ★ Terminal data FROM backend PTY → xterm display
window.omega.terminal.onData((id, data) => {
    const info = state.terminal.instances.get(id);
    if (info) info.terminal.write(data);
});

// ★ Terminal exit cleanup
window.omega.terminal.onExit((id, code) => {
    const info = state.terminal.instances.get(id);
    if (info) {
        info.terminal.write(`\r\n[Process exited with code ${code}]\r\n`);
        state.terminal.instances.delete(id);
        const tab = document.querySelector(`.terminal-tab[data-term-id="${id}"]`);
        if (tab) tab.remove();
    }
});

// ══════════════════════════════════════════════════════════════
// CHAT SYSTEM (AGENTIC + VOICE)
// ══════════════════════════════════════════════════════════════

/** v4.2: Utility — scroll chat messages container to bottom */
function scrollChat() {
    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
}

// Voice + session state
state.chat.voiceEnabled = true;  // v3.0: Omega speaks by default
state.chat.audioPlayer = null;
state.chat.messageHistory = [];  // Full session context — never lost
state.chat.abortController = null;

function toggleVoice() {
    state.chat.voiceEnabled = !state.chat.voiceEnabled;
    const btn = document.getElementById('chat-voice-btn');
    btn.textContent = state.chat.voiceEnabled ? '🔊' : '🔇';
    btn.classList.toggle('voice-active', state.chat.voiceEnabled);
    if (!state.chat.voiceEnabled) stopAudio();
}

function stopAudio() {
    if (state.chat.audioPlayer) {
        state.chat.audioPlayer.pause();
        state.chat.audioPlayer.src = '';
        state.chat.audioPlayer = null;
    }
}

async function playVoice(text) {
    if (!state.chat.voiceEnabled || !text) return;
    // Strip markdown/code for cleaner speech
    const clean = text.replace(/```[\s\S]*?```/g, ' code block ')
        .replace(/`[^`]+`/g, '')
        .replace(/[#*_>\-|]/g, '')
        .replace(/\n+/g, '. ')
        .substring(0, 800);
    console.log('[TTS] Requesting voice for:', clean.substring(0, 80));
    try {
        // Direct fetch to Flask backend — bypasses IPC
        const resp = await fetch('http://127.0.0.1:5000/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: clean }),
        });
        if (!resp.ok) {
            console.warn('[TTS] Server error:', resp.status);
            return;
        }
        const blob = await resp.blob();
        console.log('[TTS] Got audio blob:', blob.size, 'bytes');
        if (blob.size < 100) { console.warn('[TTS] Audio too small'); return; }
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        state.chat.audioPlayer = audio;
        const stopBtn = document.getElementById('chat-stop-btn');
        stopBtn.classList.add('visible');
        audio.onended = () => {
            state.chat.audioPlayer = null;
            stopBtn.classList.remove('visible');
            URL.revokeObjectURL(url);
        };
        audio.onerror = (e) => console.error('[TTS] Audio playback error:', e);
        audio.play().catch(e => console.error('[TTS] Play failed:', e));
        console.log('[TTS] Playing audio...');
    } catch (e) { console.warn('[TTS] Playback error:', e); }
}

function interruptOmega() {
    stopAudio();
    window.omega.chat.abort(state.chat.sessionId);
    state.chat.sending = false;
    document.querySelectorAll('.thinking-indicator').forEach(el => el.remove());
    document.querySelectorAll('.chat-msg.assistant').forEach(el => {
        if (el.textContent.includes('⏳')) el.remove();
    });
    if (window._thinkingTimer) { clearInterval(window._thinkingTimer); window._thinkingTimer = null; }
    if (window._thinkingStepHandler) {
        window.omega.removeListener('omega:agent-step', window._thinkingStepHandler);
        window._thinkingStepHandler = null;
    }
    document.getElementById('chat-stop-btn').classList.remove('visible');
}

/** v4.2: Live thinking indicator — dropdown with timer + step log */
function createThinkingIndicator() {
    const container = document.createElement('div');
    container.className = 'thinking-indicator';

    const header = document.createElement('div');
    header.className = 'thinking-header';
    header.innerHTML = `
        <span class="thinking-icon">Ω</span>
        <span class="thinking-label">Thinking...</span>
        <span class="thinking-timer">0.0s</span>
        <span class="thinking-toggle">▸</span>
    `;
    container.appendChild(header);

    const stepLog = document.createElement('div');
    stepLog.className = 'thinking-steps collapsed';
    container.appendChild(stepLog);

    let expanded = false;
    header.addEventListener('click', () => {
        expanded = !expanded;
        stepLog.classList.toggle('collapsed', !expanded);
        header.querySelector('.thinking-toggle').textContent = expanded ? '▾' : '▸';
    });

    const startTime = Date.now();
    const timerEl = header.querySelector('.thinking-timer');
    window._thinkingTimer = setInterval(() => {
        timerEl.textContent = `${((Date.now() - startTime) / 1000).toFixed(1)}s`;
    }, 100);

    const toolLabels = {
        'EXT:AST': 'Reading file', 'EXT:NET': 'Searching web', 'EXT:VLT': 'Querying Vault',
        'MUT:AST': 'Editing file', 'GEN:AST': 'Writing file', 'REQ:SYS': 'Running command',
        'REQ:UI': 'Opening in editor', 'LST:AST': 'Listing directory', 'GRP:AST': 'Searching code',
        'MUT:CSS': 'Updating styles', 'MUT:SYS': 'System command', 'MUT:VLT': 'Writing to Vault',
        'VFY:AST': 'Verifying file', 'REQ:NET': 'Fetching URL',
    };

    const stepHandler = (event) => {
        console.log('[THINKING] Received agent-step event:', event.phase, event);
        const labelEl = header.querySelector('.thinking-label');
        const step = document.createElement('div');
        step.className = 'thinking-step';

        switch (event.phase) {
            case 'start':
                step.innerHTML = `<span class="step-icon">🎯</span> Analyzing request...`;
                labelEl.textContent = 'Analyzing...';
                break;
            case 'provenance':
                step.innerHTML = `<span class="step-icon">📚</span> Loaded ${event.fragments} Vault fragments`;
                labelEl.textContent = 'Consulting Vault...';
                break;
            case 'thinking':
                step.innerHTML = `<span class="step-icon">🧠</span> ${event.label || `Reasoning step ${event.iteration}`}`;
                labelEl.textContent = event.label || 'Thinking...';
                break;
            case 'tool': {
                const label = toolLabels[event.tool] || event.tool;
                const argsPreview = event.args ? ` — ${event.args}` : '';
                step.innerHTML = `<span class="step-icon spinning">⚙️</span> ${label}${argsPreview}`;
                step.classList.add('active');
                labelEl.textContent = `${label}...`;
                break;
            }
            case 'tool_done': {
                const activeSteps = stepLog.querySelectorAll('.thinking-step.active');
                if (activeSteps.length > 0) {
                    const lastActive = activeSteps[activeSteps.length - 1];
                    lastActive.classList.remove('active');
                    const icon = lastActive.querySelector('.step-icon');
                    if (icon) { icon.classList.remove('spinning'); icon.textContent = event.ok ? '✅' : '❌'; }
                }
                labelEl.textContent = `${event.totalSteps} steps completed...`;
                break;
            }
            default: return;
        }
        stepLog.appendChild(step);
        if (expanded) stepLog.scrollTop = stepLog.scrollHeight;
        scrollChat();
    };

    window._thinkingStepHandler = stepHandler;
    window.omega.on('omega:agent-step', stepHandler);
    return container;
}

function destroyThinkingIndicator() {
    if (window._thinkingTimer) { clearInterval(window._thinkingTimer); window._thinkingTimer = null; }
    if (window._thinkingStepHandler) {
        window.omega.removeListener('omega:agent-step', window._thinkingStepHandler);
        window._thinkingStepHandler = null;
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text || state.chat.sending) return;

    input.value = '';
    state.chat.sending = true;

    state.chat.messageHistory.push({ role: 'user', content: text });
    addChatMessage('user', text);

    // Show live thinking indicator
    const thinkingEl = createThinkingIndicator();
    document.getElementById('chat-messages').appendChild(thinkingEl);
    scrollChat();
    document.getElementById('chat-stop-btn').classList.add('visible');

    try {
        const result = await window.omega.chat.send(text, state.chat.sessionId);
        destroyThinkingIndicator();
        thinkingEl.remove();

        let responseText = '';
        if (result.type === 'chat') {
            responseText = result.message;
            const el = addChatMessage('assistant', responseText);
            if (result.steps > 0) {
                addClickableStepsBadge(el, result.steps, result.stepLog);
            }
        } else if (result.type === 'proposals') {
            responseText = result.message;
            addChatMessage('assistant', responseText);
            for (const p of result.proposals) addProposalCard(p);
        } else if (result.type === 'error') {
            responseText = `⚠️ ${result.message}`;
            addChatMessage('assistant', responseText);
        } else {
            responseText = result.message || JSON.stringify(result);
            addChatMessage('assistant', responseText);
        }

        state.chat.messageHistory.push({ role: 'assistant', content: responseText });
        if (responseText) playVoice(responseText);
    } catch (err) {
        destroyThinkingIndicator();
        thinkingEl.remove();
        const errMsg = `❌ Error: ${err.message}`;
        addChatMessage('assistant', errMsg);
        state.chat.messageHistory.push({ role: 'assistant', content: errMsg });
    }

    state.chat.sending = false;
    document.getElementById('chat-stop-btn').classList.remove('visible');
}

/** v4.2: Clickable step badge — expand to show what tools ran */
function addClickableStepsBadge(parentEl, steps, stepLog) {
    const badge = document.createElement('div');
    badge.className = 'msg-steps clickable';
    badge.innerHTML = `⚡ ${steps} tool steps executed <span class="steps-toggle">▸</span>`;

    const details = document.createElement('div');
    details.className = 'steps-detail collapsed';

    if (stepLog && stepLog.length > 0) {
        stepLog.forEach(s => {
            const row = document.createElement('div');
            row.className = 'step-detail-row';
            const ok = s.result?.ok ? '✅' : '❌';
            // Map tool types to readable labels
            const toolIcons = { 'AST': '📝', 'NET': '🌐', 'SYS': '⚙️', 'UI': '🖥️', 'VAULT': '🗄️' };
            const tgt = (s.tool || '').split(':')[1] || '';
            const icon = toolIcons[tgt] || '🔧';
            // Extract filename from args
            let label = s.tool || 'unknown';
            const args = typeof s.args === 'string' ? s.args : (s.args?.prm || s.args?.path || '');
            if (args) {
                const basename = args.replace(/\\/g, '/').replace(/.*\//, '').replace(/^"/, '').substring(0, 50);
                if (basename) label = basename;
            }
            row.textContent = `${ok} ${icon} ${label}`;
            row.title = args || s.tool; // full path on hover
            details.appendChild(row);
        });
    } else {
        details.textContent = `${steps} tool(s) executed autonomously`;
    }

    badge.addEventListener('click', () => {
        details.classList.toggle('collapsed');
        badge.querySelector('.steps-toggle').textContent = details.classList.contains('collapsed') ? '▸' : '▾';
    });

    parentEl.appendChild(badge);
    parentEl.appendChild(details);
}

function addChatMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const welcome = container.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const msgEl = document.createElement('div');
    msgEl.className = `chat-msg ${role}`;

    if (role === 'assistant') {
        msgEl.innerHTML = renderMarkdown(content);
    } else {
        msgEl.textContent = content;
    }

    container.appendChild(msgEl);
    scrollChat();
    return msgEl;
}

function addProposalCard(proposal) {
    const container = document.getElementById('chat-messages');
    const card = document.createElement('div');
    card.className = 'chat-msg assistant';
    card.innerHTML = `
        <div style="font-size:11px;color:var(--orange)">🔐 APPROVAL REQUIRED — ${proposal.safety}</div>
        <div style="margin:4px 0"><strong>${proposal.tool}</strong></div>
        <pre style="font-size:11px">${JSON.stringify(proposal.args, null, 2)}</pre>
        <div style="display:flex;gap:8px;margin-top:8px">
            <button class="reports-action-btn" onclick="approveProposal('${proposal.id}')">✅ Approve</button>
            <button class="reports-action-btn" onclick="denyProposal('${proposal.id}')">❌ Deny</button>
        </div>
    `;
    container.appendChild(card);
    scrollChat();
}

async function approveProposal(id) {
    const btns = event?.target?.closest?.('.chat-msg')?.querySelectorAll('button');
    if (btns) btns.forEach(b => { b.disabled = true; b.style.opacity = '0.5'; });

    const thinkingEl = createThinkingIndicator();
    document.getElementById('chat-messages').appendChild(thinkingEl);
    scrollChat();

    try {
        const result = await window.omega.agent.approve(id, 'user-click');
        destroyThinkingIndicator();
        thinkingEl.remove();

        if (result.error) {
            addChatMessage('assistant', `⚠️ Approval failed: ${result.error}`);
            return;
        }

        if (result.agentResponse) {
            const resp = result.agentResponse;
            if (resp.type === 'chat' && resp.message) {
                const el = addChatMessage('assistant', resp.message);
                if (resp.steps > 0) addClickableStepsBadge(el, resp.steps, resp.stepLog);
            } else if (resp.type === 'proposals') {
                addChatMessage('assistant', resp.message);
                for (const p of resp.proposals) addProposalCard(p);
            } else if (resp.message) {
                addChatMessage('assistant', resp.message);
            }
        } else {
            // v4.3: Auto-continue after approval — show thinking, keep reasoning
            showToast('Approved ✅ — continuing...', 'success');
            const contThinkingEl = createThinkingIndicator();
            document.getElementById('chat-messages').appendChild(contThinkingEl);
            scrollChat();
            try {
                const contResult = await window.omega.chat.send(
                    'The approved action was executed successfully. Continue with the original task.',
                    state.chat.sessionId
                );
                destroyThinkingIndicator();
                contThinkingEl.remove();
                if (contResult) {
                    if (contResult.type === 'chat' && contResult.message) {
                        const el = addChatMessage('assistant', contResult.message);
                        if (contResult.steps > 0) addClickableStepsBadge(el, contResult.steps, contResult.stepLog);
                        state.chat.messageHistory.push({ role: 'assistant', content: contResult.message });
                    } else if (contResult.type === 'proposals') {
                        addChatMessage('assistant', contResult.message || 'More actions need approval:');
                        if (contResult.proposals) {
                            for (const p of contResult.proposals) addProposalCard(p);
                        }
                    } else if (contResult.message) {
                        addChatMessage('assistant', contResult.message);
                    }
                }
            } catch (contErr) {
                destroyThinkingIndicator();
                contThinkingEl.remove();
                console.warn('[APPROVE] Auto-continue failed:', contErr.message);
            }
        }
    } catch (err) {
        destroyThinkingIndicator();
        thinkingEl.remove();
        // Graceful handling for already-executed proposals (double-click or continuation race)
        if (err.message && err.message.includes('EXECUTED')) {
            showToast('Action already executed', 'success');
        } else {
            addChatMessage('assistant', `❌ Execution error: ${err.message}`);
        }
    }
}

async function denyProposal(id) {
    await window.omega.agent.deny(id, 'user-denied');
    showToast('Action denied', 'warning');
}

function renderMarkdown(text) {
    if (!text) return '';
    // v4.3: Enhanced VTP sanitization — strip ALL VTP artifacts before rendering
    let clean = text;
    // 1. Fenced vtp code blocks (```vtp ... ```)
    clean = clean.replace(/```vtp[\s\S]*?```/g, '');
    // 2. Inline VTP packet lines: REQ::, [ACT:..., ||BND:...
    clean = clean.replace(/^REQ::.*$/gm, '');
    clean = clean.replace(/^\[ACT:[^\]]*\].*$/gm, '');
    clean = clean.replace(/^\|\|BND:.*$/gm, '');
    // 3. Orphaned ``vtp or `` markers left after stripping
    clean = clean.replace(/^```\s*$/gm, '');
    // 4. Collapse multiple blank lines
    clean = clean.replace(/\n{3,}/g, '\n\n').trim();
    if (!clean) clean = '(Actions executed — see tool steps above)';
    return clean
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/^\- (.+)$/gm, '• $1')
        .replace(/^\d+\. (.+)$/gm, '<span class="md-ol">$1</span>')
        .replace(/\n/g, '<br>');
}

// ══════════════════════════════════════════════════════════════
// ACTIVITY BAR (PANEL SWITCHING)
// ══════════════════════════════════════════════════════════════

function switchPanel(panelName) {
    const sidebar = document.getElementById('sidebar');

    // Toggle collapse when clicking same panel
    if (panelName === state.activePanel && !sidebar.classList.contains('sidebar-collapsed')) {
        sidebar.classList.add('sidebar-animating');
        sidebar.classList.add('sidebar-collapsed');
        sidebar.addEventListener('transitionend', function cleanup() {
            sidebar.classList.remove('sidebar-animating');
            sidebar.removeEventListener('transitionend', cleanup);
        }, { once: true });
        requestAnimationFrame(() => state.editor?.layout());
        // Delayed layout to catch post-transition
        setTimeout(() => state.editor?.layout(), 220);
        return;
    }

    // Expand if collapsed
    if (sidebar.classList.contains('sidebar-collapsed')) {
        sidebar.classList.add('sidebar-animating');
        sidebar.classList.remove('sidebar-collapsed');
        sidebar.style.width = '';  // Clear any inline width from resize drag
        sidebar.addEventListener('transitionend', function cleanup() {
            sidebar.classList.remove('sidebar-animating');
            sidebar.removeEventListener('transitionend', cleanup);
        }, { once: true });
        setTimeout(() => state.editor?.layout(), 220);
    }
    state.activePanel = panelName;

    // Update activity bar buttons
    document.querySelectorAll('.activity-btn').forEach(btn =>
        btn.classList.toggle('active', btn.dataset.panel === panelName)
    );

    // Update sidebar panels
    document.querySelectorAll('.sidebar-panel').forEach(panel =>
        panel.classList.toggle('hidden', panel.dataset.panel !== panelName)
    );

    // Update sidebar header
    const titles = {
        explorer: 'EXPLORER', search: 'SEARCH', omega: 'Ω OMEGA',
        vault: '🧠 VERITAS VAULT', security: 'SECURITY',
        tools: 'TOOLS', ledger: 'LEDGER', settings: 'SETTINGS',
    };
    document.querySelector('.sidebar-title').textContent = titles[panelName] || panelName.toUpperCase();

    // Load panel data
    loadPanelData(panelName);

    // Relayout editor after sidebar width change
    requestAnimationFrame(() => state.editor?.layout());
}

async function loadPanelData(panel) {
    switch (panel) {
        case 'omega': await loadOmegaPanel(); break;
        case 'vault': await loadVaultPanel(); break;
        case 'security': await loadSecurityPanel(); break;
        case 'tools': await loadToolsPanel(); break;
        case 'ledger': await loadLedgerPanel(); break;
        case 'evolution': if (window.loadEvolutionPanel) await window.loadEvolutionPanel(); break;
    }
}

// ── Omega Panel ──────────────────────────────────────────────
async function loadOmegaPanel() {
    const statusEl = document.getElementById('omega-health-status');
    try {
        const status = await window.omega.status();
        statusEl.textContent = status?.status === 'READY'
            ? `✅ ONLINE — Port ${status.port}` : `⚠️ ${status?.status || 'Unknown'}`;
        statusEl.style.color = status?.status === 'READY' ? 'var(--green)' : 'var(--orange)';
    } catch {
        statusEl.textContent = '❌ Offline';
        statusEl.style.color = 'var(--red)';
    }

    // Load modules
    try {
        const modules = await window.omega.modules();
        const listEl = document.getElementById('omega-module-list');
        document.getElementById('omega-module-count').textContent = Array.isArray(modules) ? modules.length : 0;
        listEl.innerHTML = '';

        if (Array.isArray(modules)) {
            for (const mod of modules) {
                const card = document.createElement('div');
                card.className = 'omega-module-card';
                const statusClass = (mod.status || '').toLowerCase() === 'active' ? 'active'
                    : (mod.status || '').toLowerCase() === 'frozen' ? 'frozen' : 'error';
                card.innerHTML = `
                    <div class="mod-name">${mod.name || mod.id}</div>
                    <div class="mod-desc">${mod.description || ''}</div>
                    <span class="mod-status ${statusClass}">${mod.status || 'UNKNOWN'}</span>
                `;
                card.addEventListener('click', () => {
                    showToast(`Module: ${mod.id} — ${mod.status}`, 'info');
                });
                listEl.appendChild(card);
            }
        }
    } catch { }
}

// ── Vault Panel ──────────────────────────────────────────────
async function loadVaultPanel() {
    const statusEl = document.getElementById('vault-health-status');

    try {
        const ctx = await window.omega.vault.getContext();
        const ctxEl = document.getElementById('vault-context');
        if (ctx && !ctx.error) {
            const stats = ctx.stats || {};
            const recent = Array.isArray(ctx.recent) ? ctx.recent : [];
            ctxEl.innerHTML = `
                <div class="vault-stats">
                    <div class="vault-stat"><span class="vault-stat-num">${(stats.entries || 0).toLocaleString()}</span><span class="vault-stat-label">Entries</span></div>
                    <div class="vault-stat"><span class="vault-stat-num">${stats.knowledge_items || 0}</span><span class="vault-stat-label">KIs</span></div>
                    <div class="vault-stat"><span class="vault-stat-num">${stats.sessions || 0}</span><span class="vault-stat-label">Sessions</span></div>
                </div>
                ${recent.length > 0 ? recent.map(r => {
                    const typeBadge = r.type ? `<span class="vault-type-badge vault-type-${r.type}">${r.type}</span>` : '';
                    const ts = r.timestamp ? `<span class="vault-entry-time">${r.timestamp.split(' ')[0]}</span>` : '';
                    return `<div class="vault-entry" data-source="${r.source || ''}" title="${r.source || ''}">
                        <div class="vault-entry-header">${typeBadge}${ts}</div>
                        <div class="vault-entry-title">${r.title || r.source || ''}</div>
                    </div>`;
                }).join('') : ''}
            `;
            // Make entries clickable — resolve relative vault paths
            const VAULT_ROOT = 'C:\\Users\\rlope\\AppData\\Roaming\\veritas-vault\\vault_data';
            ctxEl.querySelectorAll('.vault-entry[data-source]').forEach(el => {
                el.style.cursor = 'pointer';
                el.addEventListener('click', () => {
                    let src = el.dataset.source;
                    if (src && !src.includes(':')) {
                        src = VAULT_ROOT + '\\' + src.replace(/\//g, '\\');
                    }
                    if (src) openFile(src).catch(() => {});
                });
            });
            statusEl.textContent = '✅ Connected';
            statusEl.style.color = 'var(--green)';
        } else {
            ctxEl.innerHTML = '<div class="reports-empty">Vault not connected</div>';
            statusEl.textContent = '⚠️ Not connected';
            statusEl.style.color = 'var(--orange)';
        }
    } catch {
        statusEl.textContent = '❌ Offline';
        statusEl.style.color = 'var(--red)';
    }

    try {
        const sessions = await window.omega.vault.getSessions();
        const sessEl = document.getElementById('vault-sessions');
        if (Array.isArray(sessions) && sessions.length > 0) {
            sessEl.innerHTML = sessions.slice(0, 10).map(s => {
                const docCount = s.doc_count ? `<span class="vault-doc-count">${s.doc_count} docs</span>` : '';
                return `<div class="vault-entry" data-session="${s.id || ''}" title="Session: ${s.id || ''}">
                    <div class="vault-entry-header"><span class="vault-entry-time">${s.updated_at || ''}</span>${docCount}</div>
                    <div class="vault-entry-title">${s.title || s.id || 'Untitled session'}</div>
                </div>`;
            }).join('');
        } else {
            sessEl.innerHTML = '<div class="reports-empty">No sessions found</div>';
        }
    } catch { }

    try {
        const health = await window.omega.vault.getKIHealth();
        const healthEl = document.getElementById('vault-ki-health');
        if (health && !health.error) {
            const total = health.total || 0;
            const items = Array.isArray(health.items) ? health.items : [];
            healthEl.innerHTML = `
                <div class="vault-stats">
                    <div class="vault-stat"><span class="vault-stat-num">${total}</span><span class="vault-stat-label">Total KIs</span></div>
                </div>
                ${items.slice(0, 12).map(ki => {
                    const typeBadge = ki.type ? `<span class="vault-type-badge vault-type-${ki.type}">${ki.type}</span>` : '';
                    return `<div class="vault-entry">
                        <div class="vault-entry-header">${typeBadge}<span class="vault-doc-count">${ki.doc_count || 0} docs</span></div>
                        <div class="vault-entry-title">${ki.title || ''}</div>
                    </div>`;
                }).join('')}
            `;
        } else {
            healthEl.innerHTML = '<div class="reports-empty">No KI data</div>';
        }
    } catch { }

    document.getElementById('status-vault-ctx').textContent = '🧠 Vault';
}

// ── Security Panel ───────────────────────────────────────────
async function loadSecurityPanel() {
    try {
        const scan = await window.omega.security.scan();
        const postureEl = document.getElementById('security-posture');
        if (scan && !scan.error) {
            const findings = Array.isArray(scan.findings) ? scan.findings : [];
            const count = scan.count || findings.length;
            postureEl.innerHTML = `
                <div class="vault-stats">
                    <div class="vault-stat">
                        <span class="vault-stat-num" style="${count === 0 ? 'color:var(--green)' : ''}">${count}</span>
                        <span class="vault-stat-label">Findings</span>
                    </div>
                    <div class="vault-stat">
                        <span class="vault-stat-num" style="color:${findings.filter(f => f.severity === 'high').length > 0 ? 'var(--red)' : 'var(--green)'}">${findings.filter(f => f.severity === 'high').length}</span>
                        <span class="vault-stat-label">Critical</span>
                    </div>
                    <div class="vault-stat">
                        <span class="vault-stat-num">${findings.filter(f => f.severity === 'low').length}</span>
                        <span class="vault-stat-label">Low</span>
                    </div>
                </div>
                ${findings.slice(0, 10).map(f => {
                    const sev = (f.severity || 'low').toLowerCase();
                    return `<div class="finding-card severity-${sev}">
                        <div class="finding-severity ${sev}">${sev.toUpperCase()}</div>
                        <div class="finding-detail">${f.detail || ''}</div>
                        <div class="finding-type">${f.type || ''}</div>
                    </div>`;
                }).join('')}
                ${findings.length === 0 ? '<div class="panel-status-ok">All clear — no threats detected</div>' : ''}
            `;
        }
    } catch { }
}

// ── Tools Panel ──────────────────────────────────────────────
async function loadToolsPanel() {
    try {
        const brain = await window.omega.tools.brain();
        const brainEl = document.getElementById('tools-brain');
        if (brain && !brain.error) {
            brainEl.innerHTML = `
                <div class="vault-stats">
                    <div class="vault-stat"><span class="vault-stat-num" style="color:${brain.status === 'active' ? 'var(--green)' : 'var(--orange)'}">●</span><span class="vault-stat-label">${brain.status || 'unknown'}</span></div>
                    <div class="vault-stat"><span class="vault-stat-num">${brain.nodes || 0}</span><span class="vault-stat-label">Nodes</span></div>
                    <div class="vault-stat"><span class="vault-stat-num">${brain.edges || 0}</span><span class="vault-stat-label">Edges</span></div>
                </div>
                ${Array.isArray(brain.capabilities) ? `<div style="font-size:11px;color:var(--text-secondary);padding:4px 12px">${brain.capabilities.join(' • ')}</div>` : ''}
                ${brain.last_sync ? `<div style="font-size:10px;color:var(--text-tertiary);padding:2px 12px">Last sync: ${brain.last_sync === 'never' ? 'never' : new Date(brain.last_sync).toLocaleString()}</div>` : ''}
            `;
        }
    } catch { }
}

// ── Ledger Panel (removed — consolidated into Vault) ────────

// ══════════════════════════════════════════════════════════════
// SEARCH
// ══════════════════════════════════════════════════════════════

async function performSearch() {
    const input = document.getElementById('search-input');
    const query = input.value.trim();
    if (!query || !state.workspaceDir) return;

    const results = await window.omega.search.text(state.workspaceDir, query);
    const resultsEl = document.getElementById('search-results');

    if (!Array.isArray(results) || results.length === 0) {
        resultsEl.innerHTML = '<div class="reports-empty">No results found</div>';
        return;
    }

    resultsEl.innerHTML = results.map(r => `
        <div class="search-result" data-file="${r.file}" data-line="${r.line}">
            <div class="file-path">${r.name}:${r.line}</div>
            <div class="match-text">${r.text.replace(new RegExp(query, 'gi'), m => `<span class="match-highlight">${m}</span>`)}</div>
        </div>
    `).join('');

    resultsEl.querySelectorAll('.search-result').forEach(el => {
        el.addEventListener('click', () => {
            openFile(el.dataset.file).then(() => {
                const line = parseInt(el.dataset.line);
                if (state.editor && line) {
                    state.editor.revealLineInCenter(line);
                    state.editor.setPosition({ lineNumber: line, column: 1 });
                }
            });
        });
    });
}

// ══════════════════════════════════════════════════════════════
// RESIZE HANDLES
// ══════════════════════════════════════════════════════════════

function initResizeHandles() {
    const sidebar = document.getElementById('sidebar');
    const sidebarHandle = document.getElementById('sidebar-resize');
    const chatPanel = document.getElementById('omega-chat-panel');
    const chatHandle = document.getElementById('chat-resize');
    const bottomPanel = document.getElementById('bottom-panel');
    const panelHandle = document.getElementById('panel-resize');

    makeResizable(sidebarHandle, (dx) => {
        // If collapsed, un-collapse on drag
        if (sidebar.classList.contains('sidebar-collapsed')) {
            sidebar.classList.remove('sidebar-collapsed');
            sidebar.style.width = '40px';  // Start from small width
        }
        const w = Math.max(180, Math.min(500, sidebar.offsetWidth + dx));
        sidebar.style.width = w + 'px';
        state.editor?.layout();
    });

    makeResizable(chatHandle, (dx) => {
        const w = Math.max(250, Math.min(600, chatPanel.offsetWidth - dx));
        chatPanel.style.width = w + 'px';
        state.editor?.layout();
    });

    makeResizable(panelHandle, (_, dy) => {
        const h = Math.max(100, Math.min(600, bottomPanel.offsetHeight - dy));
        bottomPanel.style.height = h + 'px';
        fitAllTerminals();
    }, true);
}

function makeResizable(handle, onDrag, isVertical = false) {
    let startX, startY;
    handle.addEventListener('mousedown', (e) => {
        startX = e.clientX; startY = e.clientY;
        handle.classList.add('active');
        document.body.style.cursor = isVertical ? 'row-resize' : 'col-resize';
        document.body.style.userSelect = 'none';
        // v4.3.5: Prevent iframes/webviews from stealing mouse events during drag
        document.querySelectorAll('iframe, webview, .xterm').forEach(el => el.style.pointerEvents = 'none');
        const onMove = (e) => {
            const dx = e.clientX - startX; const dy = e.clientY - startY;
            startX = e.clientX; startY = e.clientY;
            onDrag(dx, dy);
        };
        const onUp = () => {
            handle.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            document.querySelectorAll('iframe, webview, .xterm').forEach(el => el.style.pointerEvents = '');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    });
}

function fitAllTerminals() {
    for (const [_, info] of state.terminal.instances) {
        try { info.fitAddon.fit(); } catch { }
    }
}

// ══════════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ══════════════════════════════════════════════════════════════

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        const ctrl = e.ctrlKey || e.metaKey;

        // Ctrl+S — Save
        if (ctrl && e.key === 's') { e.preventDefault(); saveFile(); }
        // Ctrl+O — Open file
        if (ctrl && e.key === 'o') {
            e.preventDefault();
            window.omega.file.openDialog().then(r => { if (r?.path) openFile(r.path); });
        }
        // Ctrl+` — Toggle terminal
        if (ctrl && e.key === '`') {
            e.preventDefault();
            const panel = document.getElementById('bottom-panel');
            panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
        }
        // Ctrl+Shift+E — Explorer
        if (ctrl && e.shiftKey && e.key === 'E') { e.preventDefault(); switchPanel('explorer'); }
        // Ctrl+Shift+F — Search
        if (ctrl && e.shiftKey && e.key === 'F') { e.preventDefault(); switchPanel('search'); document.getElementById('search-input').focus(); }
        // Escape — Focus editor
        if (e.key === 'Escape') { state.editor?.focus(); }
    });
}

// ══════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ══════════════════════════════════════════════════════════════

function initEventListeners() {
    // Activity bar
    document.querySelectorAll('.activity-btn[data-panel]').forEach(btn => {
        btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
    });

    // Window controls
    document.getElementById('btn-minimize').addEventListener('click', () => window.omega.window.minimize());
    document.getElementById('btn-maximize').addEventListener('click', () => window.omega.window.maximize());
    document.getElementById('btn-close').addEventListener('click', () => window.omega.window.close());

    // Welcome buttons
    document.getElementById('btn-welcome-open-file')?.addEventListener('click', async () => {
        const r = await window.omega.file.openDialog();
        if (r?.path) openFile(r.path);
    });
    document.getElementById('btn-welcome-open-folder')?.addEventListener('click', async () => {
        const dir = await window.omega.file.openFolder();
        if (dir) loadFileTree(dir);
    });
    document.getElementById('btn-welcome-omega')?.addEventListener('click', () => switchPanel('omega'));

    // Open folder trigger
    document.getElementById('open-folder-trigger')?.addEventListener('click', async () => {
        const dir = await window.omega.file.openFolder();
        if (dir) loadFileTree(dir);
    });

    // Terminal
    document.getElementById('btn-new-terminal').addEventListener('click', () => createTerminal());

    // Chat
    document.getElementById('chat-send-btn').addEventListener('click', sendChatMessage);
    document.getElementById('chat-voice-btn')?.addEventListener('click', toggleVoice);
    document.getElementById('chat-stop-btn')?.addEventListener('click', interruptOmega);
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
        if (e.key === 'Escape') interruptOmega();
    });
    document.getElementById('btn-clear-chat')?.addEventListener('click', () => {
        document.getElementById('chat-messages').innerHTML = '';
        state.chat.sessionId = crypto.randomUUID();
        state.chat.messageHistory = [];  // Reset session context
        stopAudio();
        showToast('Chat cleared', 'info', 1500);
    });

    // Search
    document.getElementById('search-input')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // Vault
    document.getElementById('vault-search-btn')?.addEventListener('click', async () => {
        const query = document.getElementById('vault-search-input').value.trim();
        if (!query) return;
        const results = await window.omega.vault.search(query);
        const resultsEl = document.getElementById('vault-search-results');
        resultsEl.innerHTML = results?.error
            ? `<div class="reports-empty">${results.error}</div>`
            : (Array.isArray(results) ? results.slice(0, 15).map(r => `<div class="search-result"><div class="file-path">${r.timestamp || r.source || ''}</div><div class="match-text">${r.title || r.content || r.summary || ''}</div></div>`).join('') : '<div class="reports-empty">No results</div>');
    });
    document.getElementById('vault-sweep-btn')?.addEventListener('click', async () => {
        showToast('Intelligence sweep started...', 'info');
        const result = await window.omega.vault.sweep();
        showToast(result?.error ? `Sweep failed: ${result.error}` : 'Sweep complete!', result?.error ? 'error' : 'success');
    });
    document.getElementById('vault-refresh-btn')?.addEventListener('click', () => loadVaultPanel());

    // Reports
    document.getElementById('reports-refresh-btn')?.addEventListener('click', () => loadReportsPanel());

    // Security
    document.querySelectorAll('.shield-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const shield = btn.dataset.shield;
            const action = btn.dataset.action;
            showToast(`${shield}: ${action}...`, 'info');
            try {
                const handlers = {
                    gravity: () => window.omega.security.gravityShield(action),
                    void: () => window.omega.security.void(action),
                    basilisk: () => window.omega.security.basilisk(action),
                    nemesis: () => window.omega.security.nemesis(action),
                };
                const result = await handlers[shield]();
                showToast(result?.error || `${shield} ${action} complete`, result?.error ? 'error' : 'success');
            } catch (e) { showToast(e.message, 'error'); }
        });
    });
    document.getElementById('security-full-scan-btn')?.addEventListener('click', async () => {
        showToast('Full security scan started...', 'info');
        const result = await window.omega.security.fullScan();
        showToast(result?.error ? `Scan failed: ${result.error}` : 'Scan complete!', result?.error ? 'error' : 'success');
    });

    // Evolution
    document.getElementById('evolution-scan-btn')?.addEventListener('click', () => {
        showToast('Scanning for harness patches...', 'info');
        if (window.loadEvolutionPanel) window.loadEvolutionPanel();
    });

    // Tools
    document.getElementById('email-send-btn')?.addEventListener('click', async () => {
        const to = document.getElementById('email-to').value;
        const subject = document.getElementById('email-subject').value;
        const body = document.getElementById('email-body').value;
        if (!to || !subject) { showToast('Email: recipient and subject required', 'warning'); return; }
        const result = await window.omega.tools.sendEmail({ to, subject, body });
        showToast(result?.error || 'Email sent!', result?.error ? 'error' : 'success');
    });
    document.getElementById('review-btn')?.addEventListener('click', async () => {
        const repo = document.getElementById('review-repo').value;
        const pr = document.getElementById('review-pr').value;
        if (!repo) { showToast('Code review: repo required', 'warning'); return; }
        const result = await window.omega.tools.codeReview({ repo, pr: parseInt(pr) || undefined });
        showToast(result?.error || 'Review complete!', result?.error ? 'error' : 'success');
    });

    // Ledger
    document.getElementById('ledger-search-btn')?.addEventListener('click', async () => {
        const query = document.getElementById('ledger-search-input').value.trim();
        if (!query) return;
        const results = await window.omega.ledger.search(query);
        const entriesEl = document.getElementById('ledger-entries');
        entriesEl.innerHTML = results?.error
            ? `<div class="reports-empty">${results.error}</div>`
            : (Array.isArray(results) ? results.slice(0, 15).map(e => `<div class="search-result"><div class="file-path">${e.timestamp || ''} — ${e.module_id || ''}</div><div class="match-text">${e.action || e.data || ''}</div></div>`).join('') : '<div class="reports-empty">No results</div>');
    });
    document.getElementById('ledger-refresh-btn')?.addEventListener('click', () => loadLedgerPanel());

    // File watcher events
    window.omega.watcher.onEvent((type, path) => {
        if (['add', 'change', 'unlink'].includes(type)) {
            setTimeout(() => { if (state.workspaceDir) loadFileTree(state.workspaceDir); }, 300);
        }
    });

    // Main process menu events
    window.omega.on('menu:open-file', async () => {
        const r = await window.omega.file.openDialog();
        if (r?.path) openFile(r.path);
    });
    window.omega.on('menu:open-folder', async () => {
        const dir = await window.omega.file.openFolder();
        if (dir) loadFileTree(dir);
    });
    window.omega.on('menu:save', () => saveFile());
    window.omega.on('menu:new-terminal', () => createTerminal());
    window.omega.on('omega:backend-ready', (info) => {
        showToast(`Backend READY — port ${info.port}`, 'success');
        document.getElementById('status-bridge').textContent = 'Ω ONLINE';
        document.getElementById('status-bridge').style.color = 'var(--green)';
    });

    // Sentinel alerts — security flash + toast
    window.omega.on('omega:sentinel-alert', (alert) => {
        if (alert.severity === 'critical') {
            // Auto-heal: flash security shield red
            showToast(`🛡️ SENTINEL: ${alert.message}`, 'error', 6000);
            const securityBtn = document.querySelector('[data-panel="security"]');
            if (securityBtn) {
                securityBtn.style.animation = 'voicePulse 0.5s 6';
                securityBtn.style.color = '#e74c3c';
                setTimeout(() => { securityBtn.style.animation = ''; securityBtn.style.color = ''; }, 3000);
            }
        } else if (alert.severity === 'warning') {
            showToast(`⚠️ SENTINEL: ${alert.message}`, 'warning', 4000);
        } else {
            showToast(`🔍 SENTINEL: ${alert.message}`, 'info', 3000);
        }
    });

    // v4.3: Auto-open files in Monaco when agent writes them
    window.omega.on('omega:open-file', (filePath) => {
        if (filePath && typeof filePath === 'string') {
            console.log('[MONACO] Auto-opening agent-written file:', filePath);
            openFile(filePath);
        }
    });

    // v4.3.8: Ctrl+S file save handler
    window.omega.on('menu:save', async () => {
        const activeTab = document.querySelector('#editor-tabs .tab.active');
        if (!activeTab) return;
        const filePath = activeTab.dataset?.path;
        if (!filePath || filePath === 'welcome') {
            showToast('No file to save', 'warning');
            return;
        }
        try {
            const content = state.editor?.getValue() || '';
            await window.omega.file.save(filePath, content);
            showToast(`Saved: ${filePath.split(/[\\/]/).pop()}`, 'success', 2000);
            console.log('[SAVE] Saved file:', filePath, content.length, 'chars');
        } catch (err) {
            showToast(`Save failed: ${err.message}`, 'error');
        }
    });

    // Auto-resize
    window.addEventListener('resize', () => {
        state.editor?.layout();
        fitAllTerminals();
    });
}

// ══════════════════════════════════════════════════════════════
// EVOLUTION PANEL
// ══════════════════════════════════════════════════════════════

window.loadEvolutionPanel = async function() {
    const queueEl = document.getElementById('evolution-queue');
    const healthEl = document.getElementById('evolution-health-status');
    if (!queueEl || !healthEl) return;
    
    queueEl.innerHTML = '<div class="reports-empty">Scanning for harness patches...</div>';
    
    try {
        const resp = await fetch('http://127.0.0.1:5000/api/evolution/proposals', { headers: { 'X-Omega-Auth': 'sentinel' }});
        const proposals = await resp.json();
        
        if (!proposals || proposals.length === 0) {
            queueEl.innerHTML = '<div class="reports-empty">No pending manifests.</div>';
            healthEl.textContent = 'Stable';
            healthEl.style.color = 'var(--green)';
            return;
        }
        
        healthEl.textContent = `${proposals.length} Patches Pending`;
        healthEl.style.color = 'var(--orange)';
        
        queueEl.innerHTML = proposals.map(p => `
            <div class="search-result" style="cursor: default; padding: 12px; border: 1px solid var(--border); border-radius: 4px; margin-bottom: 8px;">
                <div class="file-path" style="font-size: 14px; font-weight: bold; color: var(--gold)">Evolution Manifest: ${p.manifest_id.substring(0,8)}</div>
                <div class="match-text" style="color: var(--text); margin-bottom: 6px;">Target: <span style="color: var(--blue)">${p.target_module}</span></div>
                <div class="match-text" style="color: var(--textSubtitle); font-size: 11px;">Rationale: ${p.rationale}</div>
                <div style="background: var(--bgDarker); padding: 8px; border-radius: 4px; margin-top: 8px; font-family: monospace; font-size: 11px; color: var(--textSubtitle); border: 1px solid var(--borderLighter);">
                    Proposed Patch:<br/><span style="color: var(--green)">${JSON.stringify(p.proposed_patch)}</span>
                </div>
                <div style="margin-top: 12px; display: flex; gap: 8px;">
                    <button class="reports-action-btn" onclick="resolveEvolution('${p.manifest_id}', 'approve')" style="color: var(--green); flex: 1; justify-content: center; background: var(--bgDarker)">Accept Re-Write</button>
                    <button class="reports-action-btn" onclick="resolveEvolution('${p.manifest_id}', 'reject')" style="color: var(--red); flex: 1; justify-content: center; background: var(--bgDarker)">Reject</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        queueEl.innerHTML = `<div class="reports-empty" style="color: var(--red)">Error loading queue: ${e.message}</div>`;
        healthEl.textContent = 'Offline';
    }
}

window.resolveEvolution = async function(id, action) {
    try {
        const resp = await fetch('http://127.0.0.1:5000/api/evolution/resolve', {
            method: 'POST',
            headers: { 'X-Omega-Auth': 'sentinel', 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, action })
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        
        showToast(`Evolution patch ${action}d successfully.`, action === 'approve' ? 'success' : 'info');
        window.loadEvolutionPanel();
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
};

// ══════════════════════════════════════════════════════════════
// SENTINEL CONTROLS
// ══════════════════════════════════════════════════════════════

window.sentinelToggle = async function(action) {
    const statusEl = document.getElementById('sentinel-status-text');
    try {
        const endpoints = { pause: '/api/sentinel/pause', resume: '/api/sentinel/resume', accept: '/api/sentinel/accept' };
        const resp = await fetch(`http://127.0.0.1:5000${endpoints[action]}`, {
            method: 'POST', headers: { 'X-Omega-Auth': 'sentinel', 'Content-Type': 'application/json' }
        });
        const data = await resp.json();
        const labels = { pause: '⏸ Paused', resume: '▶ Active', accept: '🔒 Re-Baselined' };
        statusEl.textContent = labels[action] || data.status;
        statusEl.style.color = action === 'pause' ? 'var(--orange)' : 'var(--green)';
        showToast(`Sentinel: ${labels[action]}`, 'success', 2000);
    } catch(e) {
        statusEl.textContent = '❌ Error';
        showToast(`Sentinel error: ${e.message}`, 'error');
    }
};

// ══════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════

(function init() {
    initMonaco();
    initResizeHandles();
    initKeyboardShortcuts();
    initEventListeners();

    // Auto-create first terminal
    createTerminal();

    // Load omega panel data in background
    setTimeout(() => loadOmegaPanel(), 1000);
    setTimeout(() => loadVaultPanel(), 2000);

    // Hardware polling (status bar)
    setInterval(async () => {
        try {
            const hw = await window.omega.hardware();
            if (hw.gpu) {
                document.getElementById('status-bridge').title =
                    `GPU: ${hw.gpu.name} | VRAM: ${hw.gpu.vram_used_mb}/${hw.gpu.vram_total_mb}MB`;
            }
        } catch { }
    }, 30000);

    console.log('%c Ω GRAVITY OMEGA v3.0 %c READY ',
        'background: linear-gradient(90deg, #d4a843, #a0802a); color: #000; font-weight: bold; padding: 4px 12px; border-radius: 4px;',
        'background: #1a1a1a; color: #d4a843; font-weight: bold; padding: 4px 8px;'
    );
})();
