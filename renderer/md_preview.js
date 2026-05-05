/**
 * GRAVITY OMEGA v5.2 — Markdown Preview
 * Adds a preview toggle to the editor toolbar for .md files.
 */
'use strict';

(function initMarkdownPreview() {
    const toolbar = document.getElementById('editor-toolbar');
    if (!toolbar) return;

    // Create preview button — hidden until a .md file is active
    const previewBtn = document.createElement('button');
    previewBtn.className = 'editor-toolbar-btn';
    previewBtn.id = 'btn-md-preview';
    previewBtn.title = 'Side-by-side Markdown preview (Ctrl+Shift+P)';
    previewBtn.textContent = '⊞ Split Preview';
    previewBtn.style.display = 'none';
    toolbar.appendChild(previewBtn);

    // Create preview panel
    const previewPanel = document.createElement('div');
    previewPanel.id = 'md-preview-panel';
    const editorContainer = document.getElementById('editor-container');
    if (editorContainer) {
        editorContainer.style.position = 'relative';
        editorContainer.appendChild(previewPanel);
    }

    let previewVisible = false;

    function togglePreview() {
        const file = state.activeFile;
        const isMd = file && file.toLowerCase().endsWith('.md');
        
        if (!isMd && previewVisible) {
            previewVisible = false;
            previewPanel.classList.remove('visible');
            previewBtn.classList.remove('active');
            showToast('Preview only available for .md files', 'info', 2000);
            return;
        }
        if (!isMd) {
            showToast('Open a .md file first', 'info', 2000);
            return;
        }

        previewVisible = !previewVisible;
        if (previewVisible) {
            renderMarkdown();
            previewPanel.classList.add('visible');
            previewBtn.classList.add('active');
            // Shrink editor
            const monacoEl = document.getElementById('monaco-container');
            if (monacoEl) monacoEl.style.width = '50%';
        } else {
            previewPanel.classList.remove('visible');
            previewBtn.classList.remove('active');
            const monacoEl = document.getElementById('monaco-container');
            if (monacoEl) monacoEl.style.width = '';
        }
    }

    function renderMarkdown() {
        const file = state.openFiles.get(state.activeFile);
        if (!file) return;

        const content = state.editor ? state.editor.getValue() : file.content;
        let html = content || '';

        // Simple markdown → HTML
        // Code blocks (```...```)
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function(_, lang, code) {
            return '<pre><code>' + escapeHtml(code) + '</code></pre>';
        });
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Headers
        html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        // Bold/italic
        html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
        // Images
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');
        // Horizontal rules
        html = html.replace(/^---$/gm, '<hr>');
        // Blockquotes
        html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
        // Unordered lists
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
        // Ordered lists
        html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
        // Line breaks → <br>
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        // Clean up empty paragraphs
        html = html.replace(/<p><\/p>/g, '');

        previewPanel.innerHTML = html;
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    // Auto-update preview button visibility and content when file changes
    // Use DOMContentLoaded-style defer so we hook after app.js has run
    function installSwitchHook() {
        if (typeof switchToFile !== 'function') return; // app.js not ready yet
        const orig = switchToFile;
        switchToFile = function(filePath) {
            orig(filePath);
            const isMd = filePath && filePath.toLowerCase().endsWith('.md');
            previewBtn.style.display = isMd ? '' : 'none';
            if (!isMd && previewVisible) {
                previewVisible = false;
                previewPanel.classList.remove('visible');
                previewBtn.classList.remove('active');
                const monacoEl = document.getElementById('monaco-container');
                if (monacoEl) monacoEl.style.width = '';
            }
            if (isMd && previewVisible) renderMarkdown();
        };
    }

    // Try immediately (app.js may have already run), then retry after a tick
    installSwitchHook();
    if (typeof switchToFile !== 'function' || !switchToFile._mdHooked) {
        setTimeout(installSwitchHook, 0);
    }

    previewBtn.addEventListener('click', togglePreview);

    // Keyboard shortcut: Ctrl+Shift+P
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'P') {
            e.preventDefault();
            togglePreview();
        }
    });

    console.log('[MD Preview] Initialized');
})();
