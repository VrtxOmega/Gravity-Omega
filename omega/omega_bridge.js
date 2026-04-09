/**
 * OMEGA BRIDGE v2.0 — Python Backend Process Manager
 *
 * Spawns web_server.py on port 5000, manages lifecycle:
 *   - Health polling (every 3s)
 *   - Auto-restart (5 retries, exponential backoff)
 *   - Orphan cleanup (kills any process on port before start)
 *   - Crypto handshake (OMEGA_AUTH_TOKEN)
 *   - Parent PID heartbeat (auto-terminate on crash)
 */
'use strict';

const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const crypto = require('crypto');
const EventEmitter = require('events');

const PORT = 5000;
const MAX_RETRIES = 999; // Never give up — unkillable backend
const HEALTH_INTERVAL = 60000; // Check every 60s — less noise, still catches zombies
const STARTUP_TIMEOUT = 30000;
const HEALTHY_RESET_MS = 60000; // Reset retry count after 60s of healthy operation

class OmegaBridge extends EventEmitter {
    constructor() {
        super();
        this._process = null;
        this._status = 'STOPPED';
        this._port = PORT;
        this._retries = 0;
        this._authToken = crypto.randomBytes(32).toString('hex');
        this._healthTimer = null;
        this._ready = false;
        this._startupResolve = null;
        this._lastHealthyAt = 0; // Track when backend was last known healthy
        this._respawning = false; // Prevent concurrent respawn attempts
    }

    // ── Start Backend ────────────────────────────────────────
    async start() {
        // Guard: skip if process is alive AND healthy
        if (this._process && this._ready) return;
        // Clean up dead/unhealthy process reference
        if (this._process && !this._ready) {
            try { this._process.kill('SIGKILL'); } catch { }
            this._process = null;
        }

        this._setStatus('STARTING');

        // Kill orphans on our port
        await this._killOrphans();

        // Find web_server.py
        const serverPath = this._findServer();
        if (!serverPath) {
            this._setStatus('ERROR');
            throw new Error('web_server.py not found');
        }

        // Find Python
        const python = this._findPython();
        if (!python) {
            this._setStatus('ERROR');
            throw new Error('Python not found');
        }

        return new Promise((resolve, reject) => {
            this._startupResolve = resolve;

            const env = {
                ...process.env,
                OMEGA_AUTH_TOKEN: this._authToken,
                OMEGA_PARENT_PID: String(process.pid),
                FLASK_PORT: String(this._port),
                PYTHONUNBUFFERED: '1',
            };

            // Spawn via WSL — Python backend lives on Linux side
            const wslCmd = `cd ~/gravity-omega-v2 && .venv/bin/python backend/web_server.py`;
            this._process = spawn('wsl', ['--', 'bash', '-c', wslCmd], {
                env,
                stdio: ['pipe', 'pipe', 'pipe'],
            });

            this._process.stdout.on('data', (data) => {
                const text = data.toString().trim();
                if (text) console.log(`[Bridge:stdout] ${text}`);
                if (text.includes('Running on') || text.includes('Serving Flask')) {
                    this._onReady();
                }
            });

            this._process.stderr.on('data', (data) => {
                const text = data.toString().trim();
                if (text) console.log(`[Bridge:stderr] ${text}`);
                if (text.includes('Running on') || text.includes('Serving Flask')) {
                    this._onReady();
                }
            });

            this._process.on('exit', (code) => {
                console.log(`[Bridge] Process exited with code ${code}`);
                this._process = null;
                this._ready = false;
                this._stopHealth();
                this._setStatus('STOPPED');

                if (code !== 0 && this._retries < MAX_RETRIES) {
                    this._retries++;
                    const delay = Math.min(1000 * Math.pow(2, this._retries), 30000);
                    console.log(`[Bridge] Restarting in ${delay}ms (attempt ${this._retries}/${MAX_RETRIES})`);
                    setTimeout(() => this.start().catch(() => {}), delay);
                }
            });

            this._process.on('error', (err) => {
                console.error(`[Bridge] Spawn error: ${err.message}`);
                this._setStatus('ERROR');
                this.emit('error', err);
                reject(err);
            });

            // Timeout
            setTimeout(() => {
                if (!this._ready) {
                    console.warn('[Bridge] Startup timeout — attempting health check anyway');
                    this._checkHealth().then(ok => {
                        if (ok) this._onReady();
                        else reject(new Error('Backend startup timeout'));
                    });
                }
            }, STARTUP_TIMEOUT);
        });
    }

    _onReady() {
        if (this._ready) return;
        this._ready = true;
        this._retries = 0;
        this._setStatus('READY');
        this._startHealth();
        this.emit('ready', { port: this._port, pid: this._process?.pid });
        if (this._startupResolve) {
            this._startupResolve();
            this._startupResolve = null;
        }
    }

    // ── Stop ─────────────────────────────────────────────────
    async stop() {
        this._stopHealth();
        if (this._process) {
            this._process.kill('SIGTERM');
            await new Promise(resolve => setTimeout(resolve, 1000));
            if (this._process) {
                try { this._process.kill('SIGKILL'); } catch { }
            }
            this._process = null;
        }
        this._ready = false;
        this._setStatus('STOPPED');
    }

    // ── HTTP Client ──────────────────────────────────────────
    async get(path) {
        return this._request('GET', path);
    }

    async post(path, body) {
        return this._request('POST', path, body);
    }

    async postVTP({ op, act, tgt, prm, bnd, rgm, fal, parent_seal, drift }) {
        const { VTPCodec } = require('./vtp_codec');
        const packetString = VTPCodec.encode(op, act, tgt, prm, bnd, rgm, fal, parent_seal || "GENESIS", drift);
        
        return new Promise((resolve, reject) => {
            const req = http.request({
                hostname: '127.0.0.1', port: this._port,
                path: '/vtp', method: 'POST',
                headers: {
                    'Content-Type': 'text/plain',
                    'X-Omega-Token': this._authToken,
                    'Content-Length': Buffer.byteLength(packetString)
                },
                timeout: 60000,
            }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => {
                    try { resolve(data); } catch { resolve(data); }
                });
            });
            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
            req.write(packetString);
            req.end();
        });
    }

    _request(method, reqPath, body) {
        return new Promise((resolve, reject) => {
            const payload = body ? JSON.stringify(body) : null;
            const req = http.request({
                hostname: '127.0.0.1', port: this._port,
                path: reqPath, method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Omega-Token': this._authToken,
                    ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
                },
                timeout: 300000,
            }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => {
                    try { resolve(JSON.parse(data)); }
                    catch { resolve(data); }
                });
            });
            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
            if (payload) req.write(payload);
            req.end();
        });
    }

    // ── Health ───────────────────────────────────────────────
    async waitForBridge(timeoutMs = 5000) {
        if (this._ready) return true;
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            const ok = await this._checkHealth();
            if (ok) { this._ready = true; return true; }
            await new Promise(r => setTimeout(r, 500));
        }
        return false;
    }

    async _checkHealth() {
        try {
            const result = await this.get('/api/status');
            return !!result && !result.error;
        } catch { return false; }
    }

    _startHealth() {
        this._stopHealth();
        this._lastHealthyAt = Date.now();
        this._healthTimer = setInterval(async () => {
            const ok = await this._checkHealth();
            if (ok) {
                this._lastHealthyAt = Date.now();
                // Reset retry counter after sustained healthy period
                if (this._retries > 0 && (Date.now() - this._lastHealthyAt) > HEALTHY_RESET_MS) {
                    console.log('[Bridge] Backend stable for 60s — resetting retry counter');
                    this._retries = 0;
                }
                if (!this._ready) {
                    console.log('[Bridge] Health restored — marking READY');
                    this._ready = true;
                    this._setStatus('READY');
                }
            } else if (this._ready) {
                this._ready = false;
                this._setStatus('UNHEALTHY');
                this.emit('error', new Error('Health check failed'));
                console.warn('[Bridge] Backend UNHEALTHY — triggering auto-respawn');
                this._autoRespawn();
            }
            // Poll sentinel alerts
            if (this._ready) {
                try {
                    const alertData = await this.get('/api/sentinel/alerts');
                    if (alertData && alertData.alerts && alertData.alerts.length > 0) {
                        for (const alert of alertData.alerts) {
                            this.emit('sentinel-alert', alert);
                        }
                    }
                } catch { /* non-fatal */ }
            }
        }, HEALTH_INTERVAL);
    }

    _stopHealth() {
        if (this._healthTimer) {
            clearInterval(this._healthTimer);
            this._healthTimer = null;
        }
    }

    // ── Status ───────────────────────────────────────────────
    getStatus() {
        return {
            status: this._status, port: this._port,
            ready: this._ready, pid: this._process?.pid || null,
            retries: this._retries,
        };
    }

    _setStatus(s) {
        this._status = s;
        this.emit('status', s);
    }

    // ── Auto-Respawn (triggered by health check failure) ────
    async _autoRespawn() {
        if (this._respawning) return; // Prevent concurrent respawns
        this._respawning = true;

        try {
            console.log(`[Bridge] Auto-respawn starting (attempt ${this._retries + 1})`);

            // Kill dead process if it exists
            if (this._process) {
                try { this._process.kill('SIGKILL'); } catch { }
                this._process = null;
            }

            // Brief delay before restart
            const delay = Math.min(2000 * Math.pow(1.5, Math.min(this._retries, 8)), 30000);
            console.log(`[Bridge] Respawning in ${Math.round(delay)}ms`);
            await new Promise(r => setTimeout(r, delay));

            this._retries++;

            // Restart
            await this.start();
            console.log('[Bridge] Auto-respawn SUCCEEDED');
        } catch (err) {
            console.error(`[Bridge] Auto-respawn FAILED: ${err.message}`);
            // Schedule another attempt via the health timer
            // (health timer will detect UNHEALTHY again and call _autoRespawn)
        } finally {
            this._respawning = false;
        }
    }

    // ── Helpers ──────────────────────────────────────────────
    _findServer() {
        // Server lives on WSL side — check it exists
        try {
            execSync('wsl -- test -f ~/gravity-omega-v2/backend/web_server.py', { timeout: 5000 });
            return '~/gravity-omega-v2/backend/web_server.py';
        } catch { return null; }
    }

    _findPython() {
        // Python lives on WSL side in the venv
        try {
            execSync('wsl -- ~/gravity-omega-v2/.venv/bin/python --version', { timeout: 5000, stdio: 'pipe' });
            console.log('[Bridge] Using WSL venv Python');
            return 'wsl';
        } catch { }
        try {
            execSync('wsl -- python3 --version', { timeout: 5000, stdio: 'pipe' });
            return 'wsl';
        } catch { }
        return null;
    }

    async _killOrphans() {
        try {
            const out = execSync(`wsl -- bash -c "lsof -ti :${this._port} 2>/dev/null"`, {
                encoding: 'utf-8', timeout: 3000
            }).trim();
            if (out) {
                const pids = out.split('\n').map(p => parseInt(p.trim())).filter(Boolean);
                for (const pid of pids) {
                    try { execSync(`wsl -- kill -9 ${pid}`, { timeout: 3000 }); } catch { }
                }
                if (pids.length > 0) {
                    console.log(`[Bridge] Killed ${pids.length} orphan(s) on port ${this._port}`);
                }
            }
        } catch { }
    }
}

module.exports = { OmegaBridge };
