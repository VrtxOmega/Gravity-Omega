const e = require('electron');
console.log('TYPE:', typeof e);
if (typeof e === 'string') {
    console.log('VALUE:', e);
    console.log('ELECTRON IS NOT RUNNING AS MAIN PROCESS');
} else {
    console.log('KEYS:', Object.keys(e).slice(0, 10));
    console.log('app:', typeof e.app);
    if (e.app) {
        e.app.whenReady().then(() => {
            console.log('APP IS READY');
            e.app.quit();
        });
    }
}
