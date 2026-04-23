const { OmegaAgent } = require('./omega/omega_agent');
const ag = new OmegaAgent({context:{addBreadcrumb:()=>{}}, hooks:{}, bridge:{}});
const txt = `
\`\`\`vtp
REQ::[ACT:RUN|TGT:writeFile|PRM:"{\\"path\\":\\"test.txt\\", \\"content\\":\\"line1\\\\nline2\\"}"]::[BND:NONE|RGM:SAFE|FAL:WARN]
\`\`\`
`;
console.log(JSON.stringify(ag._parseResponse(txt), null, 2));
