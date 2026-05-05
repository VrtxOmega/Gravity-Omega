/**
 * VERITAS Docs — Electron Main Process
 * ======================================
 * Launches Flask backend, creates BrowserWindow, wires IPC.
 */

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let flaskProcess;
const FLASK_PORT = 5080;
const FLASK_URL = `http://127.0.0.1:${FLASK_PORT}`;

// ── FLASK BACKEND ─────────────────────────────────────────
function startFlask() {
  const backendPath = path.join(__dirname, 'backend', 'app.py');
  flaskProcess = spawn('python', [backendPath], {
    cwd: path.join(__dirname, 'backend'),
    env: { ...process.env, FLASK_ENV: 'production' },
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true
  });

  flaskProcess.stdout.on('data', (data) => {
    console.log(`[Flask] ${data.toString().trim()}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.log(`[Flask] ${data.toString().trim()}`);
  });

  flaskProcess.on('close', (code) => {
    console.log(`[Flask] Process exited with code ${code}`);
  });
}

// ── WINDOW ────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    backgroundColor: '#080808',
    icon: path.join(__dirname, 'sovereign_docs_icon.ico'),
    title: 'VERITAS Build Dashboard',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    autoHideMenuBar: true,
    frame: true,
  });

  // Wait for Flask to be ready, then load the UI
  const waitForFlask = () => {
    const http = require('http');
    const req = http.get(`${FLASK_URL}/health`, (res) => {
      if (res.statusCode === 200) {
        mainWindow.loadURL(FLASK_URL);
      } else {
        setTimeout(waitForFlask, 500);
      }
    });
    req.on('error', () => {
      setTimeout(waitForFlask, 500);
    });
    req.setTimeout(2000, () => {
      req.destroy();
      setTimeout(waitForFlask, 500);
    });
  };

  waitForFlask();

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── IPC HANDLERS ──────────────────────────────────────────
ipcMain.handle('open-file', async (event, filePath) => {
  try {
    await shell.openPath(filePath);
    return { success: true };
  } catch (e) {
    return { success: false, error: e.message };
  }
});

ipcMain.handle('show-in-folder', async (event, filePath) => {
  shell.showItemInFolder(filePath);
  return { success: true };
});

// ── LIFECYCLE ─────────────────────────────────────────────
app.on('ready', () => {
  startFlask();
  createWindow();
});

app.on('window-all-closed', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
  app.quit();
});

app.on('before-quit', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
});
