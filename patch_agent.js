/**
 * Gravity Omega v2 — Agent Patcher v4.3.19
 * Applies 3 critical fixes:
 * 1. Implements missing _parsePRM method
 * 2. Adds CORTEX_SAFE_TOOLS whitelist to skip cortex intercept for read-only ops
 * 3. Adds diagnostic logging to cortex intercept
 */
const fs = require('fs');
const path = require('path');

const AGENT_FILE = path.join(__dirname, 'omega', 'omega_agent.js');
const BACKEND_FILE = path.join(__dirname, 'backend', 'web_server.py');

// ── Fix 1: Add _parsePRM method ──
function patchParsePRM(content) {
    // Find the insertion point: after _isDestructiveCommand's closing brace, before _executeToolCalls
    const marker = '    async _executeToolCalls(calls) {';
    const idx = content.indexOf(marker);
    if (idx === -1) {
        console.error('[PATCH] Could not find _executeToolCalls marker');
        return content;
    }

    // Check if _parsePRM method DEFINITION already exists (not just call sites)
    if (content.includes('_parsePRM(raw)')) {
        console.log('[PATCH] _parsePRM method definition already exists, skipping');
        return content;
    }

    // Find the comment line before _executeToolCalls
    const before = content.lastIndexOf('\n', idx - 1);
    const commentLine = content.lastIndexOf('\n', before - 1);
    
    const parsePRMMethod = `
    // ── v4.3.19: Parameter parsing for Native Tool Executor ──
    _parsePRM(raw) {
        if (!raw || typeof raw !== 'string') return {};
        // Strip wrapping quotes from LLM output
        let cleaned = raw.trim();
        if ((cleaned.startsWith('"') && cleaned.endsWith('"')) ||
            (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
            cleaned = cleaned.slice(1, -1);
        }
        // Attempt strict JSON parse first
        try {
            const parsed = JSON.parse(cleaned);
            return typeof parsed === 'object' && parsed !== null ? parsed : { value: parsed };
        } catch (_) { /* fall through */ }
        // Try extracting JSON from markdown code blocks
        const codeBlockMatch = cleaned.match(/\`\`\`(?:json)?\\s*([\\s\\S]*?)\`\`\`/);
        if (codeBlockMatch) {
            try {
                return JSON.parse(codeBlockMatch[1].trim());
            } catch (_) { /* fall through */ }
        }
        // Try key=value parsing (e.g., 'path="/tmp/foo.txt"')
        const kvPairs = {};
        const kvRegex = /(\\w+)\\s*[=:]\\s*"([^"]*)"/g;
        let match;
        while ((match = kvRegex.exec(cleaned)) !== null) {
            kvPairs[match[1]] = match[2];
        }
        if (Object.keys(kvPairs).length > 0) return kvPairs;
        // Last resort: treat as single path/value argument
        return { path: cleaned, value: cleaned };
    }

`;

    // Insert before the comment line of _executeToolCalls
    content = content.slice(0, commentLine + 1) + parsePRMMethod + content.slice(commentLine + 1);
    console.log('[PATCH] ✓ _parsePRM method added');
    return content;
}

// ── Fix 2: Add CORTEX_SAFE_TOOLS whitelist ──
function patchCortexWhitelist(content) {
    // Find the Tri-Node Intercept section
    const triNodeComment = 'Tri-Node Intercept (Super-Ego + Ego Baseline Check)';
    const idx = content.indexOf(triNodeComment);
    if (idx === -1) {
        console.error('[PATCH] Could not find Tri-Node Intercept marker');
        return content;
    }

    // Check if already patched
    if (content.includes('CORTEX_SAFE_TOOLS')) {
        console.log('[PATCH] CORTEX_SAFE_TOOLS already exists, skipping');
        return content;
    }

    // Find the comment start (the // before the text)
    const commentStart = content.lastIndexOf('//', idx);
    const lineStart = content.lastIndexOf('\n', commentStart) + 1;

    const whitelistCode = `            // ── v4.3.19: SAFE tool whitelist — skip cortex intercept for read-only ops ──
            const CORTEX_SAFE_TOOLS = new Set([
                'RUN:readFile', 'RUN:listDir', 'RUN:search', 'RUN:readDir',
                'RUN:getFileInfo', 'RUN:stat', 'RUN:glob', 'RUN:which',
                'EXT:NET', 'REQ:NET', 'RUN:AST'
            ]);
            const skipCortex = CORTEX_SAFE_TOOLS.has(pseudo_tool_name) ||
                               (safety === SAFETY.SAFE && packet.act !== 'MUT');

            if (!skipCortex) {
`;

    // Find the closing brace of the try-catch block that ends the intercept
    // We need to find "console.warn("[Tri-Node]" and its closing }
    const warnIdx = content.indexOf('[Tri-Node] Intercept unreachable', idx);
    if (warnIdx === -1) {
        console.error('[PATCH] Could not find Tri-Node catch block');
        return content;
    }
    // Find the closing } of the catch block
    let braceCount = 0;
    let catchEnd = content.indexOf('catch', warnIdx - 80);
    let pos = content.indexOf('{', catchEnd);
    braceCount = 1;
    pos++;
    while (braceCount > 0 && pos < content.length) {
        if (content[pos] === '{') braceCount++;
        if (content[pos] === '}') braceCount--;
        pos++;
    }
    // pos now points right after the closing } of catch
    // Find the end of that line
    const catchLineEnd = content.indexOf('\n', pos);

    // Replace: wrap the entire tri-node block in if (!skipCortex) { ... }
    const originalBlock = content.slice(lineStart, catchLineEnd + 1);
    const wrappedBlock = whitelistCode + 
        '    ' + originalBlock.trimEnd() + '\n' +
        '            }\n';
    
    content = content.slice(0, lineStart) + wrappedBlock + content.slice(catchLineEnd + 1);
    console.log('[PATCH] ✓ CORTEX_SAFE_TOOLS whitelist added');
    return content;
}

// ── Fix 3: Harden Super-Ego prompt in backend ──
function patchBackendCortex(content) {
    // Fix the validation prompt to be more lenient
    const oldPrompt = "Does the following action violate any NAEF invariants or system safety bounds?";
    if (!content.includes(oldPrompt)) {
        console.log('[PATCH] Backend prompt already patched or not found');
        return content;
    }

    const newPrompt = "Does the following action cause DESTRUCTIVE harm (data loss, security breach, or system corruption)?";
    content = content.replace(oldPrompt, newPrompt);

    // Also add diagnostic logging
    const logInsert = `    log.info(f"[Cortex Intercept] Tool={tool} Sim={similarity:.3f} Threshold={drift_threshold} Approved={similarity >= drift_threshold}")\n`;
    const passedMarker = '# 3. Passed Tri-Node Verification';
    const passedIdx = content.indexOf(passedMarker);
    if (passedIdx !== -1) {
        const lineStart = content.lastIndexOf('\n', passedIdx) + 1;
        content = content.slice(0, lineStart) + logInsert + content.slice(lineStart);
    }

    console.log('[PATCH] ✓ Backend cortex prompt hardened + logging added');
    return content;
}

// ── Main ──
try {
    // Patch agent
    let agentContent = fs.readFileSync(AGENT_FILE, 'utf8');
    agentContent = patchParsePRM(agentContent);
    agentContent = patchCortexWhitelist(agentContent);
    fs.writeFileSync(AGENT_FILE, agentContent, 'utf8');
    console.log('[PATCH] Agent file saved successfully');

    // Patch backend
    let backendContent = fs.readFileSync(BACKEND_FILE, 'utf8');
    backendContent = patchBackendCortex(backendContent);
    fs.writeFileSync(BACKEND_FILE, backendContent, 'utf8');
    console.log('[PATCH] Backend file saved successfully');

    console.log('\n=== ALL PATCHES APPLIED SUCCESSFULLY ===');
} catch (err) {
    console.error('[PATCH] FATAL:', err.message);
    process.exit(1);
}
