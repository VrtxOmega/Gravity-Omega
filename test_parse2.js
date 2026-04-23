const { OmegaAgent } = require('./omega/omega_agent');
const ag = new OmegaAgent({context:{addBreadcrumb:()=>{}}, hooks:{}, bridge:{}});
const txt = `
\`\`\`vtp
REQ::[ACT:RUN|TGT:writeFile|PRM:"{\\"path\\":\\"test.txt\\", \\"content\\":\\"line1\\\\nline2\\"}"]::[BND:NONE|RGM:SAFE|FAL:WARN]
\`\`\`
`;
const parsed = ag._parseResponse(txt);
console.log(parsed.calls[0].prm);
try {
    const jsonArgs = ag._parsePRM(parsed.calls[0].prm);
    console.log("JSON parsed:", typeof jsonArgs, jsonArgs);
} catch(e) {
    console.log("JSON PRM failed:", e.message);
}
