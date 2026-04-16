const { spawn } = require('child_process');

const proc = spawn('powershell.exe', ['-NoProfile', '-NoExit', '-Command', '-'], {
    stdio: ['pipe', 'pipe', 'pipe']
});

let output = '';
proc.stdout.on('data', d => {
    output += d.toString();
    console.log('[STDOUT] ' + JSON.stringify(d.toString()));
});
proc.stderr.on('data', d => {
    output += d.toString();
    console.log('[STDERR] ' + JSON.stringify(d.toString()));
});

setTimeout(() => {
    console.log('Sending command...');
    proc.stdin.write('echo "Hello World"\r\n');
}, 1000);

setTimeout(() => {
    console.log('Sending marker...');
    proc.stdin.write('echo "OMEGA_MARKER"\r\n');
}, 2000);

setTimeout(() => {
    console.log('Final output: ', JSON.stringify(output));
    process.exit(0);
}, 3000);
