/**
 * OMEGA APPROVAL v2.0 — Two-Phase Commit Gate
 * Immutable proposal records with audit trail.
 * Used by the agent for GATED/RESTRICTED tool approval.
 */
'use strict';

const crypto = require('crypto');

class Proposal {
    constructor({ tool, args, reason, safety }) {
        this.id = crypto.randomUUID();
        this.tool = tool;
        this.args = args;
        this.reason = reason;
        this.safety = safety;
        this.status = 'PENDING';  // PENDING → APPROVED/DENIED → EXECUTED
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

class ApprovalGate {
    constructor(maxAudit = 500) {
        this._proposals = new Map();
        this._auditLog = [];
        this._maxAudit = maxAudit;
    }

    propose(proposal) {
        this._proposals.set(proposal.id, proposal);
        this._audit('PROPOSE', proposal);
        return proposal;
    }

    approve(proposalId, by) {
        const p = this._proposals.get(proposalId);
        if (!p) throw new Error(`Proposal not found: ${proposalId}`);
        p.approve(by);
        this._audit('APPROVE', p);
        return p;
    }

    deny(proposalId, reason) {
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
        return Array.from(this._proposals.values()).filter(p => p.status === 'PENDING');
    }

    getAuditLog(n = 50) {
        return this._auditLog.slice(-n);
    }

    _audit(action, proposal) {
        this._auditLog.push({
            action, proposalId: proposal.id, tool: proposal.tool,
            status: proposal.status, ts: new Date().toISOString(),
        });
        if (this._auditLog.length > this._maxAudit) {
            this._auditLog = this._auditLog.slice(-this._maxAudit);
        }
    }
}

module.exports = { Proposal, ApprovalGate };
