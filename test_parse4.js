const { OmegaAgent } = require('./omega/omega_agent');
const ag = new OmegaAgent({context:{addBreadcrumb:()=>{}}, hooks:{}, bridge:{}});

const fc = { args: { path: "C:\\Veritas_Lab\\dashboard_server.py", content: "from flask import Flask\n\napp = Flask(__name__)" } };
const argsJson = JSON.stringify(fc.args).replace(/"/g, '\\"');
const txt = `\n\`\`\`vtp\nREQ::[ACT:RUN|TGT:writeFile|PRM:"${argsJson}"]::[BND:NONE|RGM:SAFE|FAL:WARN]\n\`\`\`\n`;

const result = ag._parseResponse(txt);
console.log(JSON.stringify(result, null, 2));

if (result.calls) {
    console.log('Parsed PRM directly:', ag._parsePRM(result.calls[0].prm));
}
