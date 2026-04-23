const { OmegaAgent } = require('./omega/omega_agent');
const ag = new OmegaAgent({context:{addBreadcrumb:()=>{}}, hooks:{}, bridge:{}});

const fc = { args: { path: "C:\\Veritas_Lab\\dashboard_server.py", content: "from flask import Flask\n\napp = Flask(__name__)" } };
const argsJson = JSON.stringify(fc.args).replace(/"/g, '\\"');
const txt = `\n\`\`\`vtp\nREQ::[ACT:RUN|TGT:writeFile|PRM:"${argsJson}"]::[BND:NONE|RGM:SAFE|FAL:WARN]\n\`\`\`\n`;

const result = ag._parseResponse(txt);
const prm = result.calls[0].prm;
let cleaned = prm.trim();
cleaned = cleaned.replace(/\\"/g, '"');

try {
    JSON.parse(cleaned);
    console.log("JSON.parse SUCCESS!");
} catch(e) {
    console.log('JSON PARSE FAILED:', e.message);
    console.log('CLEANED:', cleaned);
    console.log('P:', cleaned.indexOf('\n'));
}
