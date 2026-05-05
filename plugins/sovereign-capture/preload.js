// ===========================================================
// SovereignCapture - Preload (IPC Bridge)
// Typed API surface. Zero node access in renderer.
// ===========================================================

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('recorder', {
  // Capture
  getSources: () => ipcRenderer.invoke('get-sources'),
  saveRecording: (buffer, filename, autoSave, metadata) =>
    ipcRenderer.invoke('save-recording', { buffer, filename, autoSave, metadata }),

  // Recordings management
  listRecordings: () => ipcRenderer.invoke('list-recordings'),
  openRecording: (filePath) => ipcRenderer.invoke('open-recording', filePath),
  openRecordingsFolder: () => ipcRenderer.invoke('open-recordings-folder'),
  deleteRecording: (filePath) => ipcRenderer.invoke('delete-recording', filePath),
  probeDuration: (filePath) => ipcRenderer.invoke('probe-duration', filePath),

  // Video tools (FFmpeg)
  convertVideo: (inputPath, outputFormat, quality) =>
    ipcRenderer.invoke('convert-video', { inputPath, outputFormat, quality }),
  trimVideo: (inputPath, startSec, endSec) =>
    ipcRenderer.invoke('trim-video', { inputPath, startSec, endSec }),
  onConvertProgress: (callback) =>
    ipcRenderer.on('convert-progress', (_event, data) => callback(data)),

  // Window
  minimize: () => ipcRenderer.send('window:minimize'),
  restore: () => ipcRenderer.send('window:restore'),
  close: () => ipcRenderer.send('window:close'),

  // Global hotkey & Control
  onToggleRecording: (callback) =>
    ipcRenderer.on('toggle-recording', () => callback()),
  onControlRecord: (callback) =>
    ipcRenderer.on('control-record', (_event, data) => callback(data)),
  notifyStateChange: (stateData) =>
    ipcRenderer.send('recording-state-changed', stateData)
});
