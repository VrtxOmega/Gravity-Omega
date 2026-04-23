document.addEventListener('DOMContentLoaded', () => {
    // Mobile QR Generation UI Logic
    const btn = document.getElementById('btn-generate-qr');
    const container = document.getElementById('qr-code-container');
    const img = document.getElementById('qr-code-img');
    const statusText = document.getElementById('qr-status-text');

    if (btn) {
        btn.addEventListener('click', async () => {
            try {
                btn.innerText = 'Generating...';
                
                // Fetch the QR connection config directly from the mobile_bridge endpoint
                const res = await fetch('http://127.0.0.1:5001/api/mobile/qr');
                if (!res.ok) throw new Error('Bridge unreachable');
                
                const data = await res.json();
                
                // Set the QR image source to a robust external generator
                img.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=1&data=${encodeURIComponent(JSON.stringify(data))}`;
                
                // Reveal the UI elements
                container.classList.remove('hidden');
                statusText.classList.remove('hidden');
                btn.innerText = 'Generate Pairing QR';
            } catch (err) {
                console.error('[QR Generation Error]', err);
                btn.innerText = 'Error - Is Bridge Running?';
                setTimeout(() => btn.innerText = 'Generate Pairing QR', 3000);
            }
        });
    }
});
