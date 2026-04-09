const fs = require('fs');

let content = fs.readFileSync('c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js', 'utf8');

const TAXONOMY_STR = `
const ERROR_TAXONOMY = [
    {
        pattern: /SyntaxError|unexpected token|parsing error/i,
        strategy: "SYNTAX_ERROR: Do NOT attempt to fix by rewriting the entire file blindly. First, EXT:AST the file, locate the exact syntax fault, and use MUT:AST to selectively correct."
    },
    {
        pattern: /AssertionError|Cannot read properties of undefined|is not a function/i,
        strategy: "STATE_FAULT: The system state is not what you assumed. Stop trying to access the missing property. Insert diagnostic logs or verify the state using EXT/REQ tools."
    },
    {
        pattern: /MODULE_NOT_FOUND|Cannot find module|command not found/i,
        strategy: "MISSING_DEPENDENCY: Do not assume the module exists. If it's a python module, REQ:SYS \`pip install <module>\`. If node, \`npm install <module>\`. If it's a binary, verify it's in PATH first."
    },
    {
        pattern: /EACCES|Permission denied|ENOENT/i,
        strategy: "FILE_SYSTEM_ERROR: Verification failed on path. Do NOT retry blindly. Ensure you are executing in the correct directory or try a different path in the user workspace."
    },
    {
        pattern: /SCHEMA_FAIL/i,
        strategy: "SCHEMA_ERROR: Your VTP payload structure is invalid. Correct your JSON PRM schema based on the STRICT requirements of the target."
    }
];
`;

if (!content.includes('ERROR_TAXONOMY')) {
    content = content.replace("class OmegaAgent {", TAXONOMY_STR + "\nclass OmegaAgent {");
}

const mapRegex = /const resultSummary = results\.map\(\(r, i\) => \{\s+const call = toolCalls\[i\];\s+const status = r\.error \? 'Ã¢Â Å’ ERROR' : 'Ã¢Å“â€¦ OK';\s+const output = r\.error \|\| JSON\.stringify\(r\.result \|\| r, null, 2\);\s+const truncated = output\.length > 2000 \? output\.substring\(0, 2000\) \+ '\\n\.\.\. \(truncated\)' : output;\s+return \`### \$\{call\.tool\} \[\$\{status\}\]\\n\\\`\\\`\\\`\\n\$\{truncated\}\\n\\\`\\\`\\\`\`;\s+\}\)\.join\('\\n\\n'\);/g;

// To support the weird characters from regex match replacing:
const mapRegex1 = /const resultSummary = results\.map\(\(r, i\) => \{[\s\S]*?return `### \$\{call\.tool\} \[\$\{status\}\]\\n\\\`\\\`\\\`\\n\$\{truncated(?:[^\}]*?)\}\\n\\\`\\\`\\\``;\s*\}\)\.join\('\\n\\n'\);/g;

const replacement = `const resultSummary = results.map((r, i) => {
                        const call = toolCalls[i];
                        const status = r.error ? '❌ ERROR' : '✅ OK';
                        let output = r.error || JSON.stringify(r.result || r, null, 2);
                        
                        if (r.error) {
                            for (const tax of ERROR_TAXONOMY) {
                                if (tax.pattern.test(r.error)) {
                                    output = \`\${tax.strategy}\\n\\nRAW ERROR:\\n\${r.error}\`;
                                    break;
                                }
                            }
                        }

                        const truncated = output.length > 2000 ? output.substring(0, 2000) + '\\n... (truncated)' : output;
                        return \`### \${call.tool} [\${status}]\\n\\\`\\\`\\\`\\n\${truncated}\\n\\\`\\\`\\\`\`;
                    }).join('\\n\\n');`;

if (content.includes('const resultSummary = results.map((r, i) => {')) {
    // We'll replace it carefully by finding the string literal match
    const parts = content.split('const resultSummary = results.map((r, i) => {');
    // It should exist twice (one in agentLoop, one in continueAfterApproval)
    if (parts.length === 3) {
        let fixedContent = parts[0];
        for (let i = 1; i <= 2; i++) {
            const endIdx = parts[i].indexOf("}).join('\\n\\n');");
            if (endIdx > -1) {
                const rest = parts[i].substring(endIdx + "}).join('\\n\\n');".length);
                fixedContent += replacement.substring("const resultSummary = results.map((r, i) => {".length) + rest;
            } else {
                console.log("Could not find endIdx for parts " + i);
            }
        }
        content = fixedContent;
        console.log("Successfully replaced both map closures.");
    }
}

fs.writeFileSync('c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js', content, 'utf8');
