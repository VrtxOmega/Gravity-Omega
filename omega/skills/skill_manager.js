'use strict';
/**
 * SKILL MANAGER v1.0
 * Dynamic skill loading for Gravity Omega. Skills are additive system prompts
 * that merge into the conversation as extra { role: 'system' } messages.
 */
const path = require('path');
const fs = require('fs');

class SkillManager {
    constructor(cwd = __dirname) {
        this._skillsDir = path.resolve(cwd, 'skills');
        this._active = new Map(); // name → { module, params }
    }

    /**
     * Load a skill by filename (without .js).
     * Returns an array of { role: 'system', content: string } messages to inject.
     */
    load(name, params = {}) {
        const skillPath = path.join(this._skillsDir, `${name}.js`);
        if (!fs.existsSync(skillPath)) {
            console.warn(`[SkillManager] Skill not found: ${skillPath}`);
            return null;
        }
        // Clear require cache so edits take effect
        delete require.cache[require.resolve(skillPath)];
        const mod = require(skillPath);
        if (!mod.getSkillText) {
            console.warn(`[SkillManager] Skill ${name} missing getSkillText export`);
            return null;
        }
        const text = mod.getSkillText(params);
        this._active.set(name, { module: mod, params });
        return { role: 'system', name, content: text };
        // Note: returning the system message object; caller adds it to messages array
    }

    unload(name) {
        this._active.delete(name);
    }

    isLoaded(name) {
        return this._active.has(name);
    }

    list() {
        try {
            return fs.readdirSync(this._skillsDir)
                .filter(f => f.endsWith('.js'))
                .map(f => f.replace('.js', ''));
        } catch {
            return [];
        }
    }

    listActive() {
        return Array.from(this._active.keys());
    }

    /**
     * Build the full set of injection messages from all active skills.
     * Returns array of { role: 'system', content } messages.
     */
    buildInjections() {
        const injections = [];
        for (const [name, { module, params }] of this._active) {
            injections.push({ role: 'system', name, content: module.getSkillText(params) });
        }
        return injections;
    }
}

module.exports = { SkillManager };
