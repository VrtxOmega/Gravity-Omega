/**
 * OMEGA CONTEXT v3.0 â€” Execution Context Manager
 *
 * AutoGPT + Click + Sentry hybrid:
 *   - Breadcrumb trail (50 events) for diagnostics
 *   - Hierarchical context stack
 *   - Resource cleanup tracking
 *   - Parameter source tracking
 */
'use strict';

class OmegaContext {
    constructor() {
        this._breadcrumbs = [];
        this._maxBreadcrumbs = 50;
        this._meta = {};
        this._cleanupStack = [];
        this._activeModule = null;
        this._sessionId = null;
        this._startTime = Date.now();
    }

    // â”€â”€ Breadcrumbs (Sentry pattern) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    addBreadcrumb(category, message, data = {}, level = 'info') {
        this._breadcrumbs.push({
            category, message, data, level,
            ts: new Date().toISOString(),
            module: this._activeModule,
        });
        if (this._breadcrumbs.length > this._maxBreadcrumbs) {
            this._breadcrumbs.shift();
        }
    }

    getBreadcrumbs(n = 20) {
        return this._breadcrumbs.slice(-n);
    }

    // â”€â”€ Active Module â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    setActiveModule(moduleId) {
        const prev = this._activeModule;
        this._activeModule = moduleId;
        this.addBreadcrumb('context', `Module switch: ${prev || 'none'} â†’ ${moduleId}`);
    }

    getActiveModule() { return this._activeModule; }

    // â”€â”€ Metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    setMeta(key, value) { this._meta[key] = value; }
    getMeta(key) { return this._meta[key]; }
    getAllMeta() { return { ...this._meta }; }

    // â”€â”€ Session â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    setSession(id) { this._sessionId = id; }
    getSession() { return this._sessionId; }

    // â”€â”€ Cleanup Stack â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    onCleanup(fn) { this._cleanupStack.push(fn); }

    async close() {
        for (const fn of this._cleanupStack.reverse()) {
            try { await fn(); } catch (e) {
                console.error(`[Context] Cleanup error: ${e.message}`);
            }
        }
        this._cleanupStack = [];
    }

    // â”€â”€ Snapshot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    snapshot() {
        return {
            activeModule: this._activeModule,
            session: this._sessionId,
            meta: { ...this._meta },
            breadcrumbs: this._breadcrumbs.length,
            uptime: Math.floor((Date.now() - this._startTime) / 1000),
        };
    }
}

module.exports = { OmegaContext };
