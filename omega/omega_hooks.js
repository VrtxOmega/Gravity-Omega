/**
 * OMEGA HOOKS v2.0 — Extension Hook System
 *
 * Pluggy-style hooks with capability flags:
 *   - 10 hook specs covering lifecycle, modules, chat, security
 *   - Module tiers (ESSENTIAL, DEFAULT, OPTIONAL)
 *   - Capability bitflags (OFFLINE, NETWORK, DESTRUCTIVE)
 */
'use strict';

const HOOK_SPECS = {
    on_backend_ready:   { description: 'Backend bridge connected and healthy' },
    on_backend_error:   { description: 'Backend bridge error or health failure' },
    on_shutdown:        { description: 'Application shutting down gracefully' },
    on_module_before:   { description: 'Before a module executes' },
    on_module_after:    { description: 'After a module completes' },
    on_chat_message:    { description: 'User sent a chat message' },
    on_chat_response:   { description: 'AI generated a response' },
    on_gate_result:     { description: 'Agent tool gate decision (approve/deny/auto)' },
    on_containment:     { description: 'Containment layer blocked a request' },
    on_context_change:  { description: 'Execution context changed (module switch)' },
};

const TIER = { ESSENTIAL: 'ESSENTIAL', DEFAULT: 'DEFAULT', OPTIONAL: 'OPTIONAL' };
const CAP = { OFFLINE: 1, NETWORK: 2, DESTRUCTIVE: 4, GPU: 8, ADMIN: 16 };

class OmegaHooks {
    constructor() {
        this._handlers = {};  // hookName → [{ fn, tier, caps, name }]
        for (const hook of Object.keys(HOOK_SPECS)) {
            this._handlers[hook] = [];
        }
    }

    register(hookName, handler, { name, tier, caps } = {}) {
        if (!this._handlers[hookName]) {
            throw new Error(`Unknown hook: ${hookName}. Available: ${Object.keys(HOOK_SPECS).join(', ')}`);
        }
        this._handlers[hookName].push({
            fn: handler,
            name: name || 'anonymous',
            tier: tier || TIER.DEFAULT,
            caps: caps || 0,
        });
        // Sort by tier priority: ESSENTIAL first
        const tierOrder = { [TIER.ESSENTIAL]: 0, [TIER.DEFAULT]: 1, [TIER.OPTIONAL]: 2 };
        this._handlers[hookName].sort((a, b) => (tierOrder[a.tier] || 1) - (tierOrder[b.tier] || 1));
    }

    unregister(hookName, handlerName) {
        if (!this._handlers[hookName]) return;
        this._handlers[hookName] = this._handlers[hookName].filter(h => h.name !== handlerName);
    }

    async fire(hookName, data = {}) {
        const handlers = this._handlers[hookName];
        if (!handlers || handlers.length === 0) return;

        const results = [];
        for (const handler of handlers) {
            try {
                const result = await handler.fn(data);
                results.push({ name: handler.name, result, ok: true });
            } catch (err) {
                results.push({ name: handler.name, error: err.message, ok: false });
                // ESSENTIAL tier errors propagate
                if (handler.tier === TIER.ESSENTIAL) throw err;
            }
        }
        return results;
    }

    getSpecs() {
        return Object.entries(HOOK_SPECS).map(([name, spec]) => ({
            name, ...spec,
            handlers: (this._handlers[name] || []).length,
        }));
    }
}

module.exports = { OmegaHooks, HOOK_SPECS, TIER, CAP };
