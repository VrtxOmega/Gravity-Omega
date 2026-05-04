/**
 * GRAVITY OMEGA v5.2 — Performance Monitor
 * Real-time FPS, memory, and load time tracking.
 * Overlay widget in bottom-right corner.
 */
'use strict';

(function initPerfMonitor() {
    // Create widget
    const widget = document.createElement('div');
    widget.id = 'perf-monitor';
    widget.innerHTML = '<span id="perf-fps">FPS: --</span> | <span id="perf-mem">MEM: --</span>';
    document.body.appendChild(widget);

    // State
    const metrics = {
        loadTime: 0,
        fps: 0,
        memUsed: 0,
        memTotal: 0,
        frameCount: 0,
        lastFpsTime: performance.now(),
        visible: false,
    };

    // Record load time
    metrics.loadTime = performance.now();
    console.log('[Perf] App load time:', metrics.loadTime.toFixed(0) + 'ms');

    // FPS counter via requestAnimationFrame
    function tickFps() {
        metrics.frameCount++;
        const now = performance.now();
        const elapsed = now - metrics.lastFpsTime;

        if (elapsed >= 1000) {
            metrics.fps = Math.round((metrics.frameCount * 1000) / elapsed);
            metrics.frameCount = 0;
            metrics.lastFpsTime = now;
            updateDisplay();
        }
        requestAnimationFrame(tickFps);
    }

    // Memory snapshot (Chrome/Electron only)
    function sampleMemory() {
        if (performance.memory) {
            metrics.memUsed = Math.round(performance.memory.usedJSHeapSize / (1024 * 1024));
            metrics.memTotal = Math.round(performance.memory.totalJSHeapSize / (1024 * 1024));
        }
        updateDisplay();
    }

    function updateDisplay() {
        const fpsEl = document.getElementById('perf-fps');
        const memEl = document.getElementById('perf-mem');

        if (fpsEl) {
            let cls = metrics.fps >= 50 ? 'perf-ok' : metrics.fps >= 30 ? 'perf-warn' : 'perf-bad';
            fpsEl.innerHTML = `FPS: <span class="${cls}">${metrics.fps}</span>`;
        }
        if (memEl) {
            if (metrics.memUsed > 0) {
                let cls = metrics.memUsed < 100 ? 'perf-ok' : metrics.memUsed < 200 ? 'perf-warn' : 'perf-bad';
                memEl.innerHTML = `MEM: <span class="${cls}">${metrics.memUsed}MB</span>`;
            } else {
                memEl.innerHTML = 'MEM: --';
            }
        }
    }

    function toggle() {
        metrics.visible = !metrics.visible;
        if (metrics.visible) {
            widget.classList.add('visible');
        } else {
            widget.classList.remove('visible');
        }
    }

    // Expose globally
    window.togglePerfMonitor = toggle;
    window.getPerfMetrics = function() { return { ...metrics }; };

    // Keyboard shortcut: Ctrl+Shift+M
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'M') {
            e.preventDefault();
            toggle();
        }
    });

    // Start monitoring
    tickFps();
    setInterval(sampleMemory, 2000);

    console.log('[Perf Monitor] Initialized (Ctrl+Shift+M to toggle)');
})();
