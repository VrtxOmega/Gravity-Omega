
const bootScreen = document.getElementById('boot-screen');
const bootLines = [
    "Initializing Aegis Protocol...",
    "Establishing secure connection to Veritas Core...",
    "Decrypting Sovereign memory blocks [OK]",
    "Loading visual payload cluster...",
    "Verifying system integrity...",
    "Executing Omega kernel modules...",
    "System diagnostics complete. All systems nominal.",
    "VERITAS OMEGA: ACCESS GRANTED"
];

let lineIndex = 0;

function typeBootLine() {
    if (lineIndex < bootLines.length) {
        const line = document.createElement('div');
        line.classList.add('boot-line');
        line.textContent = bootLines[lineIndex];
        bootScreen.appendChild(line);
        lineIndex++;
        const delay = Math.random() * 500 + 200; // Random delay between 200ms and 700ms
        setTimeout(typeBootLine, delay);
    } else {
        showAccessGrantedPanel();
    }
}

function showAccessGrantedPanel() {
    const panel = document.createElement('div');
    panel.id = 'access-granted-panel';
    const heading = document.createElement('h1');
    heading.textContent = "VERITAS OMEGA: ACCESS GRANTED";
    const time = document.createElement('p');
    time.id = 'current-time';
    panel.appendChild(heading);
    panel.appendChild(time);
    document.body.appendChild(panel);
    panel.style.display = 'block'; // Make it visible

    function updateTime() {
        const now = new Date();
        time.textContent = now.toLocaleTimeString();
    }
    updateTime();
    setInterval(updateTime, 1000); // Update time every second
}

document.addEventListener('DOMContentLoaded', () => {
    typeBootLine();
});
