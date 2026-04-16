const pty = require('node-pty');

const ptyProcess = pty.spawn('powershell.exe', ['-NoProfile', '-NoExit'], {
    name: 'omega-pty',
    cols: 80,
    rows: 30,
    cwd: process.cwd(),
    env: process.env
});

let output = '';
ptyProcess.onData((data) => {
    output += data;
    console.log('[PTY] ' + JSON.stringify(data));
});

setTimeout(() => {
    console.log('Sending command...');
    ptyProcess.write('echo "Hello World"\r');
}, 1000);

setTimeout(() => {
    console.log('Sending UUID marker...');
    ptyProcess.write('echo "OMEGA_MARKER"\r');
}, 2000);

setTimeout(() => {
    console.log('Final output buffer:', JSON.stringify(output));
    process.exit(0);
}, 3000);
