// ===========================================================
// SovereignCapture - Main Process
// High-assurance Electron capture app: record, convert, trim.
// FFmpeg-powered video pipeline. Local only.
// ===========================================================

const { app, BrowserWindow, ipcMain, dialog, desktopCapturer, globalShortcut, screen, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execFile, spawn } = require('child_process');
const http = require('http');
const crypto = require('crypto');

let mainWindow;
let apiAutoSave = false;
let activeRecordingState = { active: false, startTime: null, metadata: null };
let recordingsDir = path.join(os.homedir(), 'Videos');
let ffmpegPath;

// Resolve FFmpeg binary
try {
  ffmpegPath = require('ffmpeg-static');
} catch (e) {
  ffmpegPath = 'ffmpeg'; // Fallback to system FFmpeg
}

// ===========================================================
// WINDOW
// ===========================================================
function createWindow() {
  const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 460,
    height: 680,
    x: screenWidth - 480,
    y: 20,
    resizable: true,
    alwaysOnTop: true,
    frame: false,
    transparent: false,
    backgroundColor: '#06060e',
    icon: path.join(__dirname, 'icon.png'),
    title: 'SovereignCapture',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile('index.html');
  mainWindow.setAlwaysOnTop(true, 'screen-saver');
}

// ===========================================================
// IPC - CAPTURE SOURCES
// ===========================================================
ipcMain.handle('get-sources', async () => {
  const sources = await desktopCapturer.getSources({
    types: ['screen', 'window'],
    thumbnailSize: { width: 150, height: 150 },
    fetchWindowIcons: true
  });
  return sources.map(s => ({
    id: s.id,
    name: s.name,
    thumbnail: s.thumbnail.toDataURL(),
    appIcon: s.appIcon ? s.appIcon.toDataURL() : null,
    isScreen: s.id.startsWith('screen:')
  }));
});

// ===========================================================
// IPC - SAVE RECORDING
// ===========================================================
ipcMain.handle('save-recording', async (_event, { buffer, filename, autoSave, metadata }) => {
  let filePath;

  if (autoSave || apiAutoSave || (metadata && metadata.autoSave)) {
    // Auto-save: no dialog, straight to ~/Videos
    if (!fs.existsSync(recordingsDir)) fs.mkdirSync(recordingsDir, { recursive: true });
    filePath = path.join(recordingsDir, filename || `capture-${Date.now()}.webm`);
    apiAutoSave = false; // reset after save
  } else {
    const result = await dialog.showSaveDialog(mainWindow, {
      title: 'Save Capture',
      defaultPath: path.join(recordingsDir, filename || `capture-${Date.now()}.webm`),
      filters: [
        { name: 'WebM Video', extensions: ['webm'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    if (result.canceled || !result.filePath) return { saved: false };
    filePath = result.filePath;
  }

  recordingsDir = path.dirname(filePath);
  if (!fs.existsSync(recordingsDir)) fs.mkdirSync(recordingsDir, { recursive: true });
  fs.writeFileSync(filePath, Buffer.from(buffer));

  // Provenance / SEAL Chain Hashing
  try {
    const fileBuffer = fs.readFileSync(filePath);
    const hash = crypto.createHash('sha256');
    hash.update(fileBuffer);
    const sha256 = hash.digest('hex');
    
    if (metadata) {
       const webhookUrl = metadata.webhookUrl || 'http://127.0.0.1:5055/api/seal';
       const durationMs = activeRecordingState.startTime ? (Date.now() - activeRecordingState.startTime) : 0;
       
       const sealRecord = {
         sha256,
         filePath,
         capturedAt: new Date().toISOString(),
         triggeredBy: metadata.triggeredBy || 'unknown',
         veritasJobId: metadata.veritasJobId || 'unknown'
       };
       
       const payload = JSON.stringify({
         action: 'recording_saved',
         sessionTag: metadata.sessionTag,
         veritasJobId: metadata.veritasJobId,
         durationMs,
         sealRecord
       });
       
       try {
         const urlObj = new URL(webhookUrl);
         const client = urlObj.protocol === 'https:' ? require('https') : http;
         const webhookReq = client.request(webhookUrl, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
         });
         webhookReq.on('error', (e) => console.log('[Webhook Error]', e.message));
         webhookReq.write(payload);
         webhookReq.end();
       } catch (err) {
         console.log('[Webhook URI parse error]', err.message);
       }
    }
  } catch(e) {
    console.error('[Provenance Error]', e);
  }

  return { saved: true, path: filePath };
});

ipcMain.on('recording-state-changed', (_event, stateData) => {
  activeRecordingState.active = stateData.started;
  if (stateData.started) {
    activeRecordingState.startTime = Date.now();
    activeRecordingState.metadata = stateData.metadata || null;
  }
});

// ===========================================================
// IPC - LIST RECORDINGS
// ===========================================================
ipcMain.handle('list-recordings', async () => {
  try {
    if (!fs.existsSync(recordingsDir)) return [];
    const videoExts = ['.webm', '.mp4', '.mov', '.avi', '.mkv', '.gif'];
    const files = fs.readdirSync(recordingsDir)
      .filter(f => videoExts.includes(path.extname(f).toLowerCase()))
      .map(f => {
        const fullPath = path.join(recordingsDir, f);
        const stat = fs.statSync(fullPath);
        return {
          name: f,
          path: fullPath,
          ext: path.extname(f).toLowerCase().slice(1),
          size: stat.size,
          date: stat.mtime.toISOString()
        };
      })
      .sort((a, b) => new Date(b.date) - new Date(a.date));
    return files;
  } catch (e) {
    return [];
  }
});

// ===========================================================
// IPC - OPEN / DELETE RECORDINGS
// ===========================================================
ipcMain.handle('open-recording', (_event, filePath) => {
  shell.openPath(filePath);
});

ipcMain.handle('open-recordings-folder', () => {
  shell.openPath(recordingsDir);
});

ipcMain.handle('delete-recording', async (_event, filePath) => {
  try {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      return { deleted: true };
    }
    return { deleted: false, error: 'File not found' };
  } catch (e) {
    return { deleted: false, error: e.message };
  }
});

// ===========================================================
// IPC - PROBE DURATION (FFmpeg)
// ===========================================================
ipcMain.handle('probe-duration', async (_event, filePath) => {
  return new Promise((resolve) => {
    const proc = spawn(ffmpegPath, ['-i', filePath, '-f', 'null', '-'], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stderr = '';
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('close', () => {
      const match = stderr.match(/Duration:\s*(\d+):(\d+):(\d+)/);
      if (match) {
        const secs = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseInt(match[3]);
        resolve({ duration: secs, formatted: `${match[2]}:${match[3]}` });
      } else {
        resolve({ duration: 0, formatted: '--:--' });
      }
    });
    proc.on('error', () => resolve({ duration: 0, formatted: '--:--' }));
  });
});

// ===========================================================
// IPC - CONVERT VIDEO (FFmpeg)
// ===========================================================
ipcMain.handle('convert-video', async (_event, { inputPath, outputFormat, quality }) => {
  return new Promise(async (resolve) => {
    const ext = outputFormat || 'mp4';
    const baseName = path.basename(inputPath, path.extname(inputPath));
    const outputPath = path.join(path.dirname(inputPath), `${baseName}.${ext}`);

    // If file exists, add timestamp
    const finalPath = fs.existsSync(outputPath)
      ? path.join(path.dirname(inputPath), `${baseName}-${Date.now()}.${ext}`)
      : outputPath;

    // Build FFmpeg args based on format
    const args = ['-i', inputPath, '-y'];

    switch (ext) {
      case 'mp4':
        args.push('-c:v', 'libx264', '-preset', 'fast');
        args.push('-crf', quality === 'high' ? '18' : quality === 'low' ? '28' : '23');
        args.push('-c:a', 'aac', '-b:a', '128k');
        args.push('-movflags', '+faststart');
        break;
      case 'mov':
        args.push('-c:v', 'libx264', '-preset', 'fast', '-crf', '20');
        args.push('-c:a', 'aac', '-b:a', '192k');
        break;
      case 'gif':
        args.push('-vf', 'fps=12,scale=640:-1:flags=lanczos');
        args.push('-loop', '0');
        break;
      case 'avi':
        args.push('-c:v', 'libx264', '-crf', '23');
        break;
      default:
        args.push('-c:v', 'libx264', '-crf', '23');
    }

    args.push(finalPath);

    const proc = spawn(ffmpegPath, args, { stdio: ['pipe', 'pipe', 'pipe'] });

    let stderr = '';
    proc.stderr.on('data', (d) => {
      stderr += d.toString();
      const timeMatch = d.toString().match(/time=(\d+):(\d+):(\d+)/);
      if (timeMatch && mainWindow) {
        const secs = parseInt(timeMatch[1]) * 3600 + parseInt(timeMatch[2]) * 60 + parseInt(timeMatch[3]);
        mainWindow.webContents.send('convert-progress', { seconds: secs });
      }
    });

    proc.on('close', (code) => {
      if (code === 0 && fs.existsSync(finalPath)) {
        const stat = fs.statSync(finalPath);
        resolve({
          success: true,
          path: finalPath,
          name: path.basename(finalPath),
          size: stat.size
        });
      } else {
        resolve({ success: false, error: stderr.slice(-500) });
      }
    });

    proc.on('error', (e) => {
      resolve({ success: false, error: e.message });
    });
  });
});

// ===========================================================
// IPC - TRIM VIDEO (FFmpeg)
// ===========================================================
ipcMain.handle('trim-video', async (_event, { inputPath, startSec, endSec }) => {
  return new Promise((resolve) => {
    const baseName = path.basename(inputPath, path.extname(inputPath));
    const ext = path.extname(inputPath);
    const outputPath = path.join(
      path.dirname(inputPath),
      `${baseName}-trimmed-${Date.now()}${ext}`
    );

    const duration = endSec - startSec;
    const args = [
      '-i', inputPath,
      '-ss', String(startSec),
      '-t', String(duration),
      '-c', 'copy',
      '-y',
      outputPath
    ];

    const proc = spawn(ffmpegPath, args, { stdio: ['pipe', 'pipe', 'pipe'] });

    let stderr = '';
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('close', (code) => {
      if (code === 0 && fs.existsSync(outputPath)) {
        const stat = fs.statSync(outputPath);
        resolve({
          success: true,
          path: outputPath,
          name: path.basename(outputPath),
          size: stat.size
        });
      } else {
        resolve({ success: false, error: stderr.slice(-500) });
      }
    });

    proc.on('error', (e) => {
      resolve({ success: false, error: e.message });
    });
  });
});

// ===========================================================
// WINDOW CONTROLS
// ===========================================================
ipcMain.on('window:minimize', () => mainWindow?.minimize());
ipcMain.on('window:restore', () => { mainWindow?.restore(); mainWindow?.focus(); });
ipcMain.on('window:close', () => mainWindow?.close());

// ===========================================================
// APP LIFECYCLE
// ===========================================================
app.whenReady().then(() => {
  createWindow();

  globalShortcut.register('CommandOrControl+Shift+R', () => {
    mainWindow?.webContents.send('toggle-recording');
  });

  // Start HTTP API
  const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
    if (req.method === 'OPTIONS') {
      res.writeHead(200);
      return res.end();
    }
    
    // --- STATUS ENDPOINT ---
    if (req.method === 'GET' && req.url === '/api/record/status') {
      const elapsedSeconds = activeRecordingState.active && activeRecordingState.startTime 
        ? Math.floor((Date.now() - activeRecordingState.startTime) / 1000) 
        : 0;
        
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({
        active: activeRecordingState.active,
        elapsedSeconds,
        sessionTag: activeRecordingState.metadata?.sessionTag || null,
        veritasJobId: activeRecordingState.metadata?.veritasJobId || null
      }));
    }
    
    // --- DEPRECATED TOGGLE ENDPOINT ---
    if (req.method === 'POST' && req.url === '/api/record/toggle') {
      if (mainWindow) {
        apiAutoSave = true;
        mainWindow.webContents.send('control-record', { action: 'toggle', metadata: null });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ success: true, warning: 'Endpoint deprecated. Use /api/record/control' }));
      } else {
        res.writeHead(500);
        return res.end(JSON.stringify({ error: 'No window' }));
      }
    }
    
    // --- CONTROL ENDPOINT (NEW) ---
    if (req.method === 'POST' && req.url === '/api/record/control') {
      let body = '';
      req.on('data', chunk => body += chunk.toString());
      req.on('end', () => {
        try {
          const payload = body ? JSON.parse(body) : { action: 'toggle' };
          if (mainWindow) {
            mainWindow.webContents.send('control-record', { 
              action: payload.action || 'toggle', 
              metadata: payload 
            });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({ success: true, action: payload.action }));
          } else {
            res.writeHead(500);
            return res.end(JSON.stringify({ error: 'No window' }));
          }
        } catch (e) {
          res.writeHead(400);
          return res.end(JSON.stringify({ error: 'Invalid JSON payload' }));
        }
      });
      return;
    }

    res.writeHead(404);
    res.end();
  });
  server.listen(5060, '127.0.0.1', () => {
    console.log('SovereignCapture API listening on port 5060');
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => app.quit());
