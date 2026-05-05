/**
 * GRAVITY OMEGA — Unified Provider Registry v1.0
 *
 * Manages LLM provider configurations with encrypted API key storage
 * via Electron safeStorage. Supports any OpenAI-compatible endpoint.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');
const http = require('http');

let safeStorage = null;
try {
    safeStorage = require('electron').safeStorage;
} catch {
    // safeStorage only available in main process
}

const FALLBACK_CONFIG_DIR = path.join(os.homedir(), '.gravity-omega');
let CONFIG_DIR = FALLBACK_CONFIG_DIR;
let CONFIG_FILE = path.join(CONFIG_DIR, 'providers.json');

const DEFAULT_PROVIDERS = {
    'ollama-cloud': {
        name: 'Ollama Cloud',
        baseUrl: 'https://ollama.com/v1',
        models: [
            'deepseek-v4-pro',
            'deepseek-v4-flash',
            'deepseek-v3.1:671b',
            'qwen3.6-plus',
            'qwen3.5:397b',
            'qwen3-coder:480b',
            'qwen3-vl:235b',
            'gpt-oss:120b',
            'gpt-oss:20b',
            'glm-5.1',
            'glm-4.6',
            'llama3.3:70b',
            'llama4-maverick',
            'mistral-small:24b',
            'mistral-small:3.2',
            'phi4:14b',
            'command-r7b',
        ],
        requiresKey: true,
    },
    'kimi': {
        name: 'Kimi (Moonshot)',
        baseUrl: 'https://api.moonshot.cn/v1',
        models: [
            'kimi-k2.6',
            'kimi-k2.5',
            'kimi-k2',
            'kimi-k2-32k',
            'kimi-k2-1m',
            'kimi-k1.6',
            'kimi-k1.6-32k',
            'kimi-k1.5',
            'kimi-k1.5-long',
        ],
        requiresKey: true,
    },
    'openai': {
        name: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        models: [
            'gpt-5.5',
            'gpt-5.4',
            'gpt-5.3-instant',
            'gpt-5.2-instant',
            'gpt-4o',
            'gpt-4o-mini',
            'gpt-4.1',
            'gpt-4.1-nano',
            'o3',
            'o4-mini',
            'o1',
        ],
        requiresKey: true,
    },
    'ollama-local': {
        name: 'Local Ollama',
        baseUrl: 'http://localhost:11434/v1',
        models: [
            'qwen3:8b',
            'qwen3:14b',
            'qwen3:30b',
            'qwen3:32b',
            'qwen2.5:7b',
            'qwen2.5:14b',
            'qwen2.5:32b',
            'qwen2.5:3b',
            'qwen2.5:72b',
            'gemma3:4b',
            'gemma3:12b',
            'gemma3:27b',
            'gemma2:9b',
            'gemma2:27b',
            'deepseek-r1:7b',
            'deepseek-r1:14b',
            'deepseek-r1:32b',
            'deepseek-coder-v2:16b',
            'phi4-mini',
            'phi4:14b',
            'llama3.3:70b',
            'llama3.2:3b',
            'llama3.2:1b',
            'llama3.1:8b',
            'llama4-maverick',
            'mistral-small:24b',
            'mistral-small:3.2',
            'nomic-embed-text',
            'veritas-omni:latest',
            'gemma2:sentinel-omega',
        ],
        requiresKey: false,
    },
    'groq': {
        name: 'Groq',
        baseUrl: 'https://api.groq.com/openai/v1',
        models: [
            'llama-3.3-70b-versatile',
            'llama-3.1-8b-instant',
            'mixtral-8x7b-32768',
            'gemma2-9b-it',
            'qwen-2.5-32b-instruct',
            'deepseek-r1-distill-llama-70b',
        ],
        requiresKey: true,
    },
    'gemini': {
        name: 'Google Gemini',
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/',
        models: [
            'gemini-2.5-flash-preview-04-21',
            'gemini-2.5-pro-preview-03-25',
            'gemini-2.0-flash',
            'gemini-2.0-flash-lite',
            'gemini-1.5-pro',
            'gemini-1.5-flash',
        ],
        requiresKey: true,
    },
    'xai': {
        name: 'xAI (Grok)',
        baseUrl: 'https://api.x.ai/v1',
        models: [
            'grok-3-beta',
            'grok-3-mini-beta',
            'grok-2-1212',
        ],
        requiresKey: true,
    },
    'custom': {
        name: 'Custom (OpenAI-compatible)',
        baseUrl: 'https://api.openai.com/v1',
        models: ['custom-model'],
        requiresKey: true,
    },
    'hermes-acp': {
        name: 'Hermes ACP',
        type: 'agent_backend',
        models: ['hermes-acp'],
        requiresKey: false,
    },
};

class ProviderManager {
    constructor(configDir) {
        if (configDir) {
            CONFIG_DIR = configDir;
            CONFIG_FILE = path.join(CONFIG_DIR, 'providers.json');
        }
        this._config = this._loadConfig();
        this._ensureDefaults();
    }

    // ── Config Persistence ─────────────────────────────────────────

    _loadConfig() {
        try {
            if (fs.existsSync(CONFIG_FILE)) {
                const raw = fs.readFileSync(CONFIG_FILE, 'utf-8');
                return JSON.parse(raw);
            }
        } catch (e) {
            console.warn('[ProviderManager] Failed to load config:', e.message);
        }
        return { activeProvider: null, providers: {} };
    }

    _saveConfig() {
        try {
            if (!fs.existsSync(CONFIG_DIR)) {
                fs.mkdirSync(CONFIG_DIR, { recursive: true });
            }
            fs.writeFileSync(CONFIG_FILE, JSON.stringify(this._config, null, 2));
        } catch (e) {
            console.error('[ProviderManager] Failed to save config:', e.message);
        }
    }

    _ensureDefaults() {
        // Seed provider entries if missing
        for (const [id, def] of Object.entries(DEFAULT_PROVIDERS)) {
            if (!this._config.providers[id]) {
                this._config.providers[id] = {
                    apiKey: null,
                    baseUrl: def.baseUrl,
                    customModels: [],
                };
            }
        }
    }

    // ── Encryption ─────────────────────────────────────────────────

    _encrypt(plain) {
        if (!plain) return null;
        if (!safeStorage || !safeStorage.isEncryptionAvailable()) {
            // Fallback: base64 obfuscation (not secure, but functional in dev)
            console.warn('[ProviderManager] safeStorage unavailable — using base64 fallback');
            return { _enc: 'base64', v: Buffer.from(plain).toString('base64') };
        }
        return { _enc: 'safeStorage', v: safeStorage.encryptString(plain).toString('base64') };
    }

    _decrypt(cipher) {
        if (!cipher) return null;
        if (typeof cipher === 'string') return cipher; // legacy plain text
        if (cipher._enc === 'base64') {
            return Buffer.from(cipher.v, 'base64').toString('utf-8');
        }
        if (cipher._enc === 'safeStorage' && safeStorage) {
            return safeStorage.decryptString(Buffer.from(cipher.v, 'base64'));
        }
        return null;
    }

    // ── Public API ─────────────────────────────────────────────────

    /**
     * Reload config from disk to pick up external changes.
     */
    reload() {
        this._config = this._loadConfig();
        this._ensureDefaults();
    }

    /**
     * List all providers with their configuration status.
     * Returns array of { id, name, type, requiresKey, configured, baseUrl, models }.
     */
    listProviders() {
        this.reload(); // always fresh
        return Object.entries(DEFAULT_PROVIDERS).map(([id, def]) => {
            const cfg = this._config.providers[id] || {};
            const key = this._decrypt(cfg.apiKey);
            const models = cfg.customModels?.length > 0
                ? [...def.models, ...cfg.customModels]
                : def.models;
            return {
                id,
                name: def.name,
                type: def.type || 'openai_compatible',
                requiresKey: def.requiresKey,
                configured: !def.requiresKey || !!key,
                baseUrl: cfg.baseUrl || def.baseUrl,
                models,
                hasCustomModels: (cfg.customModels || []).length > 0,
            };
        });
    }

    /**
     * Get the currently active provider with decrypted key.
     * Returns { id, name, type, baseUrl, apiKey, model } or null.
     */
    getActiveProvider() {
        this.reload(); // always fresh
        const id = this._config.activeProvider;
        if (!id) return null;

        const def = DEFAULT_PROVIDERS[id];
        if (!def) return null;

        const cfg = this._config.providers[id] || {};
        const apiKey = this._decrypt(cfg.apiKey);

        if (def.requiresKey && !apiKey) {
            console.warn(`[ProviderManager] Provider ${id} requires API key but none configured`);
            return null;
        }

        // Pick default model
        const models = cfg.customModels?.length > 0
            ? [...def.models, ...cfg.customModels]
            : def.models;

        return {
            id,
            name: def.name,
            type: def.type || 'openai_compatible',
            baseUrl: cfg.baseUrl || def.baseUrl,
            apiKey,
            model: models[0],
            models,
        };
    }

    /**
     * Set the active provider by ID.
     */
    setActiveProvider(id) {
        if (!DEFAULT_PROVIDERS[id]) {
            throw new Error(`Unknown provider: ${id}`);
        }
        this._config.activeProvider = id;
        this._saveConfig();
        console.log(`[ProviderManager] Active provider set to: ${id}`);
        return { ok: true, id };
    }

    /**
     * Save configuration for a specific provider.
     * @param {string} id — provider ID
     * @param {object} config — { apiKey?, baseUrl?, customModels? }
     */
    saveProviderConfig(id, config) {
        if (!DEFAULT_PROVIDERS[id]) {
            throw new Error(`Unknown provider: ${id}`);
        }
        if (!this._config.providers[id]) {
            this._config.providers[id] = {};
        }
        const cfg = this._config.providers[id];

        if (config.apiKey !== undefined) {
            cfg.apiKey = config.apiKey ? this._encrypt(config.apiKey) : null;
        }
        if (config.baseUrl !== undefined) {
            cfg.baseUrl = config.baseUrl || DEFAULT_PROVIDERS[id].baseUrl;
        }
        if (config.customModels !== undefined) {
            cfg.customModels = Array.isArray(config.customModels)
                ? config.customModels
                : (config.customModels || '').split(',').map(s => s.trim()).filter(Boolean);
        }

        this._saveConfig();
        console.log(`[ProviderManager] Config saved for provider: ${id}`);
        return { ok: true };
    }

    /**
     * Test a provider connection with a lightweight request.
     * Returns { ok: boolean, latencyMs: number, error? }.
     */
    async testProvider(id) {
        const def = DEFAULT_PROVIDERS[id];
        if (!def) return { ok: false, error: `Unknown provider: ${id}` };

        const cfg = this._config.providers[id] || {};
        const baseUrl = cfg.baseUrl || def.baseUrl;
        const apiKey = this._decrypt(cfg.apiKey);

        if (def.requiresKey && !apiKey) {
            return { ok: false, error: 'API key not configured' };
        }

        const start = Date.now();

        // For OpenAI-compatible providers, try GET /models
        if (!def.type || def.type === 'openai_compatible') {
            try {
                const parsed = new URL(baseUrl);
                const options = {
                    hostname: parsed.hostname,
                    port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
                    path: '/models',
                    method: 'GET',
                    headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
                    timeout: 15000,
                };

                const result = await new Promise((resolve, reject) => {
                    const client = parsed.protocol === 'https:' ? https : http;
                    const req = client.request(options, (res) => {
                        let data = '';
                        res.on('data', c => data += c);
                        res.on('end', () => {
                            if (res.statusCode >= 200 && res.statusCode < 300) {
                                resolve({ ok: true });
                            } else {
                                reject(new Error(`HTTP ${res.statusCode}: ${data.substring(0, 200)}`));
                            }
                        });
                    });
                    req.on('error', reject);
                    req.on('timeout', () => reject(new Error('Timeout')));
                    req.end();
                });

                return { ok: true, latencyMs: Date.now() - start };
            } catch (e) {
                // Fallback: try a minimal chat completion
                try {
                    const parsed = new URL(baseUrl);
                    const payload = JSON.stringify({
                        model: def.models[0],
                        messages: [{ role: 'user', content: 'hi' }],
                        max_tokens: 5,
                    });
                    const options = {
                        hostname: parsed.hostname,
                        port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
                        path: '/chat/completions',
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
                        },
                        timeout: 15000,
                    };

                    await new Promise((resolve, reject) => {
                        const client = parsed.protocol === 'https:' ? https : http;
                        const req = client.request(options, (res) => {
                            let data = '';
                            res.on('data', c => data += c);
                            res.on('end', () => {
                                if (res.statusCode >= 200 && res.statusCode < 300) {
                                    resolve();
                                } else {
                                    reject(new Error(`HTTP ${res.statusCode}: ${data.substring(0, 200)}`));
                                }
                            });
                        });
                        req.on('error', reject);
                        req.on('timeout', () => reject(new Error('Timeout')));
                        req.write(payload);
                        req.end();
                    });

                    return { ok: true, latencyMs: Date.now() - start };
                } catch (e2) {
                    return { ok: false, error: e2.message, latencyMs: Date.now() - start };
                }
            }
        }

        // Agent backends — just check if we can start the channel
        if (def.type === 'agent_backend') {
            return { ok: true, latencyMs: Date.now() - start };
        }

        return { ok: false, error: 'Unknown provider type' };
    }

    /**
     * Auto-detect best default provider on first run.
     * Prefer local Ollama if it responds, else leave unset.
     */
    async autoDetectDefault() {
        if (this._config.activeProvider) return this._config.activeProvider;

        try {
            const result = await this.testProvider('ollama-local');
            if (result.ok) {
                this.setActiveProvider('ollama-local');
                console.log('[ProviderManager] Auto-selected: ollama-local');
                return 'ollama-local';
            }
        } catch (e) {
            console.log('[ProviderManager] Local Ollama not detected');
        }

        return null;
    }
}

module.exports = { ProviderManager, DEFAULT_PROVIDERS };
