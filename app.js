
const logOutput = document.getElementById('log-output');

const systemLogs = [
    "INIT: Veritas Protocol 7.1.2 engaged...",
    "STATUS: Global Memory Array nominal. 98.7% capacity.",
    "ALERT: Sub-agent [ALPHA-7] reporting anomalous data stream. Investigating...",
    "LOG: Initiating data integrity check on Veritas_Lab/Project_Veritas_Legacy.hc...",
    "STATUS: Active Protocol [GUARDIAN] maintaining perimeter integrity.",
    "LOG: System diagnostics complete. No critical errors detected.",
    "ALERT: Unauthorized access attempt detected on port 443. Firewall engaged.",
    "STATUS: Quantum entanglement module online. Processing data packets.",
    "LOG: Syncing with Veritas Vault. Data transfer rate: 1.2 TB/s.",
    "INIT: Deploying counter-intrusion protocols. Threat neutralized.",
    "STATUS: All systems nominal. Awaiting further directives."
];

let logIndex = 0;
let charIndex = 0;

function typeLog() {
    if (logIndex < systemLogs.length) {
        const currentLog = systemLogs[logIndex];
        if (charIndex < currentLog.length) {
            logOutput.innerHTML += currentLog.charAt(charIndex);
            charIndex++;
            setTimeout(typeLog, 50); // Typing speed
        } else {
            logOutput.innerHTML += '<br>'; // New line after each log
            logIndex++;
            charIndex = 0;
            setTimeout(typeLog, 1500); // Delay before next log
        }
    } else {
        logIndex = 0; // Loop back to the beginning
        logOutput.innerHTML = ''; // Clear terminal for fresh loop
        setTimeout(typeLog, 1500); // Delay before restarting
    }
}

typeLog();
