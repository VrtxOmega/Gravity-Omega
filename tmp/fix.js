const fs = require('fs');
let content = fs.readFileSync('c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js', 'utf8');

// The lines we want to match exactly (using includes/replace to avoid utf8 regex issues)
const badDestructive = `                    } else {
                    results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval — destructive command' });
                } else {`;

const goodDestructive = `                    } else {
                        results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval — destructive command' });
                    }
                } else {`;

// The RESTRICTED block
const badRestricted = `            } else {
                const proposal = this._createVTPProposal(packet);
                results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval — RESTRICTED operation' });
            }`;

const goodRestricted = `            } else {
                const proposal = this._createVTPProposal(packet);
                if (proposal._cached) {
                    this.context.addBreadcrumb('agent', \`Auto-executing cached proposal: \${pseudo_tool_name}\`);
                    const execRes = await this.executeApproved(proposal.id, 'session-cache');
                    results.push(execRes.result || { ok: true, note: 'auto-approved from cache' });
                } else {
                    results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval — RESTRICTED operation' });
                }
            }`;

// We also need to fix executeApproved
const badApprove = `        console.log('[APPROVE] Starting approval for:', proposalId, 'hasPendingMessages:', !!this._pendingMessages, 'pendingProposals:', this._pendingProposals.size);
        proposal.approve(confirmText || 'user-approved');
        this._pendingProposals.delete(proposalId);`;

const goodApprove = `        console.log('[APPROVE] Starting approval for:', proposalId, 'hasPendingMessages:', !!this._pendingMessages, 'pendingProposals:', this._pendingProposals.size);
        proposal.approve(confirmText || 'user-approved');
        
        // v4.3.29: Session-Scoped Permission Cache
        this.gate.grant_permission(proposal.tool, proposal.args);
        
        this._pendingProposals.delete(proposalId);`;


// Because of UTF-8 garbling like Ã¢â‚¬â€ , we can match purely using regex on the non-garbled parts.
content = content.replace(
    /\} else \{\s+results\.push\(\{ pending: true, proposalId: proposal\.id, tool: pseudo_tool_name, message: 'Requires approval[^']+destructive command' \}\);\s+\} else \{/g,
    "} else {\n                        results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval — destructive command' });\n                    }\n                } else {"
);

// Restricted
content = content.replace(
    /\} else \{\s+const proposal = this\._createVTPProposal\(packet\);\s+results\.push\(\{ pending: true, proposalId: proposal\.id, tool: pseudo_tool_name, message: 'Requires approval[^']+RESTRICTED operation' \}\);\s+\}/g,
    "} else {\n                const proposal = this._createVTPProposal(packet);\n                if (proposal._cached) {\n                    this.context.addBreadcrumb('agent', `Auto-executing cached proposal: ${pseudo_tool_name}`);\n                    const execRes = await this.executeApproved(proposal.id, 'session-cache');\n                    results.push(execRes.result || { ok: true, note: 'auto-approved from cache' });\n                } else {\n                    results.push({ pending: true, proposalId: proposal.id, tool: pseudo_tool_name, message: 'Requires approval — RESTRICTED operation' });\n                }\n            }"
);

// Approve
content = content.replace(
    /proposal\.approve\(confirmText \|\| 'user-approved'\);\s+this\._pendingProposals\.delete\(proposalId\);/g,
    "proposal.approve(confirmText || 'user-approved');\n        this.gate.grant_permission(proposal.tool, proposal.args);\n        this._pendingProposals.delete(proposalId);"
);

fs.writeFileSync('c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js', content, 'utf8');
console.log('Fixed omega_agent.js via regex overrides.');
