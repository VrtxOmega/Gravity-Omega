const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');
const { spawn } = require('child_process');
const axios = require('axios');
const os = require('os');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');
const { contextBridge, ipcRenderer } = require('electron');

// Import Monaco theme configuration BEFORE BrowserWindow creation
require('./monaco_theme_config');

// Configure logging for auto-updater
autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = 'info';

// Set up the backend bridge
const backendBridge = axios.create({
    baseURL: 'http://127.0.0.1:5000',
    timeout: 120000, // 120 seconds
});

// Function to check if the backend is running
async function checkBackendStatus() {
    try {
        const response = await backendBridge.get('/api/status');
        return response.status === 200 && response.data.status === 'online';
    } catch (error) {
        return false;
    }
}

// Function to start the Python backend
let pythonProcess = null;
function startPythonBackend() {
    if (pythonProcess) {
        console.log('Python backend already running.');
        return;
    }

    const pythonScriptPath = path.join(__dirname, '..', 'backend', 'web_server.py');
    console.log(`Attempting to start Python backend at: ${pythonScriptPath}`);

    // Use 'python' for Windows, 'python3' for WSL/Linux
    const pythonExecutable = os.platform() === 'win32' ? 'python' : 'python3';

    pythonProcess = spawn(pythonExecutable, [pythonScriptPath], {
        cwd: path.join(__dirname, '..', 'backend'),
        stdio: ['ignore', 'pipe', 'pipe'], // Ignore stdin, pipe stdout and stderr
        shell: true // Use shell to find python executable in PATH
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python stdout: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python stderr: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python backend process exited with code ${code}`);
        pythonProcess = null;
        // Optionally restart if it was an unexpected exit
        if (code !== 0) {
            console.log('Python backend crashed, attempting to restart...');
            setTimeout(startPythonBackend, 5000); // Wait 5 seconds before restarting
        }
    });

    pythonProcess.on('error', (err) => {
        console.error('Failed to start Python backend process:', err);
        dialog.showErrorBox('Backend Error', `Failed to start Python backend: ${err.message}. Please ensure Python is installed and in your PATH.`);
    });
}

// Kill Python backend process on app exit
app.on('will-quit', () => {
    if (pythonProcess) {
        console.log('Killing Python backend process...');
        pythonProcess.kill();
        pythonProcess = null;
    }
});

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1600,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        icon: path.join(__dirname, '..', 'assets', 'omega_icon.ico'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false, // Disable remote module for security
            sandbox: true // Enable sandbox for renderer process
        }
    });

    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

    // Open the DevTools.
    // mainWindow.webContents.openDevTools();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Handle new window creation (e.g., from target="_blank" links)
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url); // Open external links in default browser
        return { action: 'deny' }; // Prevent Electron from creating a new window
    });
}

app.whenReady().then(async () => {
    startPythonBackend();

    // Wait for backend to be online before creating the window
    let backendOnline = false;
    let attempts = 0;
    const maxAttempts = 10;
    const delay = 2000; // 2 seconds

    while (!backendOnline && attempts < maxAttempts) {
        console.log(`Waiting for backend to come online... Attempt ${attempts + 1}/${maxAttempts}`);
        backendOnline = await checkBackendStatus();
        if (!backendOnline) {
            await new Promise(resolve => setTimeout(resolve, delay));
            attempts++;
        }
    }

    if (!backendOnline) {
        dialog.showErrorBox('Backend Error', 'Python backend failed to start or respond after multiple attempts. Please check the console for errors.');
        app.quit();
        return;
    }

    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });

    // Check for updates after the app is ready
    // autoUpdater.checkForUpdatesAndNotify();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// IPC Handlers for backend communication
ipcMain.handle('backend:get', async (event, { path, params }) => {
    try {
        const response = await backendBridge.get(path, { params });
        return { data: response.data, status: response.status };
    } catch (error) {
        console.error(`Backend GET error for ${path}:`, error.message);
        return { error: error.message, status: error.response ? error.response.status : 500 };
    }
});

ipcMain.handle('backend:post', async (event, { path, data }) => {
    try {
        const response = await backendBridge.post(path, data);
        return { data: response.data, status: response.status };
    } catch (error) {
        console.error(`Backend POST error for ${path}:`, error.message);
        return { error: error.message, status: error.response ? error.response.status : 500 };
    }
});

// IPC Handler for executing shell commands
ipcMain.handle('sys:exec', async (event, command) => {
    return new Promise((resolve) => {
        exec(command, { shell: 'powershell.exe', timeout: 120000 }, (error, stdout, stderr) => {
            if (error) {
                console.error(`exec error: ${error}`);
                resolve({ error: error.message, stdout, stderr });
                return;
            }
            if (stderr) {
                console.warn(`stderr: ${stderr}`);
            }
            resolve({ stdout, stderr });
        });
    });
});

// IPC Handler for file operations
ipcMain.handle('file:read', async (event, filePath) => {
    try {
        const content = await fs.promises.readFile(filePath, 'utf8');
        return { content };
    } catch (error) {
        console.error(`Error reading file ${filePath}:`, error);
        return { error: error.message };
    }
});

ipcMain.handle('file:write', async (event, { filePath, content }) => {
    try {
        await fs.promises.writeFile(filePath, content, 'utf8');
        return { success: true };
    } catch (error) {
        console.error(`Error writing file ${filePath}:`, error);
        return { error: error.message };
    }
});

ipcMain.handle('file:edit', async (event, { filePath, find, replace }) => {
    try {
        let content = await fs.promises.readFile(filePath, 'utf8');
        content = content.replace(find, replace);
        await fs.promises.writeFile(filePath, content, 'utf8');
        return { success: true };
    } catch (error) {
        console.error(`Error editing file ${filePath}:`, error);
        return { error: error.message };
    }
});

ipcMain.handle('file:listDir', async (event, { dirPath, recursive = false }) => {
    try {
        const files = await listDirectoryRecursive(dirPath, recursive);
        return { files };
    } catch (error) {
        console.error(`Error listing directory ${dirPath}:`, error);
        return { error: error.message };
    }
});

async function listDirectoryRecursive(dirPath, recursive) {
    let results = [];
    const entries = await fs.promises.readdir(dirPath, { withFileTypes: true });

    for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        if (entry.isDirectory()) {
            results.push({ name: entry.name, path: fullPath, type: 'directory' });
            if (recursive) {
                results = results.concat(await listDirectoryRecursive(fullPath, true));
            }
        } else {
            const stats = await fs.promises.stat(fullPath);
            results.push({ name: entry.name, path: fullPath, type: 'file', size: stats.size });
        }
    }
    return results;
}

ipcMain.handle('file:findFiles', async (event, { directory, pattern }) => {
    try {
        const files = await findFilesRecursive(directory, pattern);
        return { files };
    } catch (error) {
        console.error(`Error finding files in ${directory} with pattern ${pattern}:`, error);
        return { error: error.message };
    }
});

async function findFilesRecursive(directory, pattern) {
    let results = [];
    const entries = await fs.promises.readdir(directory, { withFileTypes: true });
    const regex = new RegExp(pattern.replace(/\./g, '\.').replace(/\*/g, '.*')); // Convert glob to regex

    for (const entry of entries) {
        const fullPath = path.join(directory, entry.name);
        if (entry.isDirectory()) {
            results = results.concat(await findFilesRecursive(fullPath, pattern));
        } else if (regex.test(entry.name)) {
            results.push(fullPath);
        }
    }
    return results;
}

ipcMain.handle('file:createDir', async (event, dirPath) => {
    try {
        await fs.promises.mkdir(dirPath, { recursive: true });
        return { success: true };
    } catch (error) {
        console.error(`Error creating directory ${dirPath}:`, error);
        return { error: error.message };
    }
});

ipcMain.handle('file:delete', async (event, { filePath, recursive = false }) => {
    try {
        await fs.promises.rm(filePath, { recursive, force: true });
        return { success: true };
    } catch (error) {
        console.error(`Error deleting file/directory ${filePath}:`, error);
        return { error: error.message };
    }
});

ipcMain.handle('file:info', async (event, filePath) => {
    try {
        const stats = await fs.promises.stat(filePath);
        return {
            size: stats.size,
            birthtime: stats.birthtime.toISOString(),
            mtime: stats.mtime.toISOString(),
            isDirectory: stats.isDirectory(),
            isFile: stats.isFile()
        };
    } catch (error) {
        console.error(`Error getting file info for ${filePath}:`, error);
        return { error: error.message };
    }
});

ipcMain.handle('app:openFile', async (event, filePath) => {
    try {
        shell.openPath(filePath);
        return { success: true };
    } catch (error) {
        console.error(`Error opening file ${filePath}:`, error);
        return { error: error.message };
    }
});

// IPC for auto-updater
ipcMain.on('update:check', () => {
    autoUpdater.checkForUpdatesAndNotify();
});

ipcMain.on('update:install', () => {
    autoUpdater.quitAndInstall();
});

autoUpdater.on('checking-for-update', () => {
    mainWindow.webContents.send('update:status', 'Checking for update...');
});
autoUpdater.on('update-available', (info) => {
    mainWindow.webContents.send('update:status', 'Update available.');
    mainWindow.webContents.send('update:available', info);
});
autoUpdater.on('update-not-available', (info) => {
    mainWindow.webContents.send('update:status', 'Update not available.');
});
autoUpdater.on('error', (err) => {
    mainWindow.webContents.send('update:status', 'Error in auto-updater: ' + err);
});
autoUpdater.on('download-progress', (progressObj) => {
    let log_message = 'Download speed: ' + progressObj.bytesPerSecond;
    log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
    log_message = log_message + ' (' + progressObj.transferred + '/' + progressObj.total + ')';
    mainWindow.webContents.send('update:status', log_message);
});
autoUpdater.on('update-downloaded', (info) => {
    mainWindow.webContents.send('update:status', 'Update downloaded; will install on exit.');
    mainWindow.webContents.send('update:downloaded', info);
});
