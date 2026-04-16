
const blipContainer = document.getElementById('blipContainer');
const intrusionCountDisplay = document.getElementById('intrusionCount');
const cleanPayloadCountDisplay = document.getElementById('cleanPayloadCount');
const uptimeDisplay = document.getElementById('uptime');

let intrusionAttempts = 0;
let cleanPayloads = 0;
let uptimeSeconds = 0;

function updateUptime() {
    uptimeSeconds++;
    const hours = String(Math.floor(uptimeSeconds / 3600)).padStart(2, '0');
    const minutes = String(Math.floor((uptimeSeconds % 3600) / 60)).padStart(2, '0');
    const seconds = String(uptimeSeconds % 60).padStart(2, '0');
    uptimeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
}

function spawnBlip() {
    const x = Math.random() * blipContainer.offsetWidth;
    const y = Math.random() * blipContainer.offsetHeight;

    const isIntrusion = Math.random() > 0.5;

    const blip = document.createElement('div');
    blip.classList.add('blip');
    if (isIntrusion) {
        blip.classList.add('intrusion');
        intrusionAttempts++;
        intrusionCountDisplay.textContent = intrusionAttempts;
    } else {
        blip.classList.add('clean');
        cleanPayloads++;
        cleanPayloadCountDisplay.textContent = cleanPayloads;
    }
    blip.style.left = `${x}px`;
    blip.style.top = `${y}px`;
    blipContainer.appendChild(blip);

    const banner = document.createElement('div');
    banner.classList.add('warning-banner');
    if (isIntrusion) {
        banner.textContent = 'Intrusion Attempt Detected!';
    } else {
        banner.classList.add('clean-banner');
        banner.textContent = 'Clean Payload Confirmed.';
    }
    banner.style.left = `${x + 20}px`; // Offset banner from blip
    banner.style.top = `${y - 10}px`;
    blipContainer.appendChild(banner);

    // Remove blip and banner after their animation
    blip.addEventListener('animationend', () => blip.remove());
    banner.addEventListener('animationend', () => banner.remove());
}

// Initialize counts
intrusionCountDisplay.textContent = intrusionAttempts;
cleanPayloadCountDisplay.textContent = cleanPayloads;

// Set intervals for updates
setInterval(updateUptime, 1000);
setInterval(spawnBlip, 1000); // Spawn a blip every second
