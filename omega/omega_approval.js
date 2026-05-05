/**
 * OMEGA APPROVAL v4.1 â€” Two-Phase Commit Gate
 * Immutable proposal records with audit trail.
 * Used by the agent for GATED/RESTRICTED tool approval.
 *
 * v5.3 additions:
 *  - NDJSON audit log persistence with SHA-256 chain hash (tamper-evident).
 *  - 30-minute proposal TTL: pending proposals are auto-denied if not
 *    decided in time, preventing stale approval prompts from accumulating.
 */
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

class Proposal {
    constructor({ tool, args, reason, safety }) {
        this.id = crypto.randomUUID();
        this.tool = tool;
        this.args = args;
        this.reason = reason;
        this.safety = safety;
        this.status = 'PENDING';  // PENDING â†’ APPROVED/DENIED â†’ EXECUTED
        this.createdAt = new Date().toISOString();
        this.decidedAt = null;
        this.decidedBy = null;
        this.executionResult = null;
        this.executedAt = null;
    }

    approve(by) {
        if (this.status !== 'PENDING') throw new Error(`Cannot approve proposal in state: ${this.status}`);
        this.status = 'APPROVED';
        this.decidedAt = new Date().toISOString();
        this.decidedBy = by;
    }

    deny(reason) {
        if (this.status !== 'PENDING') throw new Error(`Cannot deny proposal in state: ${this.status}`);
        this.status = 'DENIED';
        this.decidedAt = new Date().toISOString();
        this.decidedBy = reason;
    }

    recordExecution(result) {
        if (this.status !== 'APPROVED') throw new Error(`Cannot execute proposal in state: ${this.status}`);
        this.status = 'EXECUTED';
        this.executionResult = result;
        this.executedAt = new Date().toISOString();
    }

    toJSON() {
        return {
            id: this.id, tool: this.tool, args: this.args,
            reason: this.reason, safety: this.safety, status: this.status,
            createdAt: this.createdAt, decidedAt: this.decidedAt,
            decidedBy: this.decidedBy, executedAt: this.executedAt,
            executionResult: this.executionResult,
        };
    }
}

// 30 minutes — pending proposals expire after this and become DENIED.
const DEFAULT_PROPOSAL_TTL_MS = 30 * 60 * 1000;

class ApprovalGate {
    /**
     * @param {object|number} opts  Options object, or maxAudit number for back-compat.
     * @param {number} [opts.maxAudit=500]      Max in-memory audit entries.
     * @param {string} [opts.auditLogPath]      If set, append each entry to this NDJSON file.
     * @param {number} [opts.proposalTtlMs]     Pending proposal TTL. Default 30 min.
     */
    constructor(opts = {}) {
        // Back-compat: ApprovalGate(500) → treat as { maxAudit: 500 }
        if (typeof opts === 'number') opts = { maxAudit: opts };
        this._proposals = new Map();
        this._auditLog = [];
        this._maxAudit = opts.maxAudit ?? 500;
        this._auditLogPath = opts.auditLogPath || null;
        this._proposalTtlMs = opts.proposalTtlMs ?? DEFAULT_PROPOSAL_TTL_MS;
        this._permissionCache = new Set();
        this._lastEntryHash = 'GENESIS'; // chain head for tamper-evident NDJSON

        // If persistence is enabled, ensure the directory exists and recover
        // the chain head from the last line so subsequent runs continue the
        // hash chain instead of restarting at GENESIS.
        if (this._auditLogPath) {
            try {
                fs.mkdirSync(path.dirname(this._auditLogPath), { recursive: true });
                if (fs.existsSync(this._auditLogPath)) {
                    const tail = fs.readFileSync(this._auditLogPath, 'utf-8').trim().split('\n');
                    const lastLine = tail[tail.length - 1];
                    if (lastLine) {
                        try { this._lastEntryHash = JSON.parse(lastLine).entry_hash || 'GENESIS'; } catch {}
                    }
                }
            } catch (e) {
                console.error('[ApprovalGate] audit log init failed:', e.message);
            }
        }

        // Sweep expired proposals every minute.
        this._ttlSweepTimer = setInterval(() => this._sweepExpired(), 60_000);
        if (this._ttlSweepTimer.unref) this._ttlSweepTimer.unref();
    }

    /** Stop the TTL sweep timer (call on shutdown). */
    dispose() {
        if (this._ttlSweepTimer) { clearInterval(this._ttlSweepTimer); this._ttlSweepTimer = null; }
    }

    _getCacheKey(tool, args) {
        const hashStr = `${tool}::${JSON.stringify(args || {})}`;
        return crypto.createHash('sha256').update(hashStr).digest('hex');
    }

    check_permission_cache(tool, args) {
        const key = this._getCacheKey(tool, args);
        return this._permissionCache.has(key);
    }

    grant_permission(tool, args) {
        const key = this._getCacheKey(tool, args);
        this._permissionCache.add(key);
        this._writeAudit({ action: 'CACHE_GRANT', tool, ts: new Date().toISOString() });
    }

    clear_permission_cache() {
        this._permissionCache.clear();
        this._writeAudit({ action: 'CACHE_CLEAR', ts: new Date().toISOString() });
    }

    propose(proposal) {
        this._sweepExpired();
        this._proposals.set(proposal.id, proposal);
        this._audit('PROPOSE', proposal);
        return proposal;
    }

    approve(proposalId, by) {
        this._sweepExpired();
        const p = this._proposals.get(proposalId);
        if (!p) throw new Error(`Proposal not found: ${proposalId}`);
        p.approve(by);
        this._audit('APPROVE', p);
        return p;
    }

    deny(proposalId, reason) {
        this._sweepExpired();
        const p = this._proposals.get(proposalId);
        if (!p) throw new Error(`Proposal not found: ${proposalId}`);
        p.deny(reason);
        this._audit('DENY', p);
        return p;
    }

    recordExecution(proposalId, result) {
        const p = this._proposals.get(proposalId);
        if (!p) throw new Error(`Proposal not found: ${proposalId}`);
        p.recordExecution(result);
        this._audit('EXECUTE', p);
        return p;
    }

    getPending() {
        this._sweepExpired();
        return Array.from(this._proposals.values()).filter(p => p.status === 'PENDING');
    }

    getAuditLog(n = 50) {
        return this._auditLog.slice(-n);
    }

    /**
     * Auto-deny pending proposals older than _proposalTtlMs.
     * Called lazily from propose/approve/deny/getPending and from a 60s timer.
     */
    _sweepExpired() {
        const now = Date.now();
        for (const p of this._proposals.values()) {
            if (p.status !== 'PENDING') continue;
            const ageMs = now - new Date(p.createdAt).getTime();
            if (ageMs > this._proposalTtlMs) {
                try {
                    p.deny('TTL_EXPIRED');
                    this._audit('TTL_EXPIRE', p);
                } catch {}
            }
        }
    }

    _audit(action, proposal) {
        this._writeAudit({
            action, proposalId: proposal.id, tool: proposal.tool,
            status: proposal.status, ts: new Date().toISOString(),
        });
    }

    /**
     * Append an entry to the in-memory log and (if configured) the NDJSON file.
     * Each entry carries prev_hash + entry_hash so tampering with any line
     * breaks the chain from that point forward.
     */
    _writeAudit(entry) {
        const enriched = { ...entry, prev_hash: this._lastEntryHash };
        const canonical = JSON.stringify(enriched, Object.keys(enriched).sort());
        const entry_hash = crypto.createHash('sha256').update(canonical).digest('hex');
        const finalEntry = { ...enriched, entry_hash };
        this._lastEntryHash = entry_hash;

        this._auditLog.push(finalEntry);
        if (this._auditLog.length > this._maxAudit) {
            this._auditLog = this._auditLog.slice(-this._maxAudit);
        }

        if (this._auditLogPath) {
            try {
                fs.appendFileSync(this._auditLogPath, JSON.stringify(finalEntry) + '\n');
            } catch (e) {
                console.error('[ApprovalGate] audit log write failed:', e.message);
            }
        }
    }
}

module.exports = { Proposal, ApprovalGate };
