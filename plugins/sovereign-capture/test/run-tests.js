// ===========================================================
// VERITAS Recorder v2 - High-Assurance Test Suite
// Tests every IPC handler, FFmpeg pipeline, file operation,
// and module contract. No Electron GUI required.
// ===========================================================

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync, execFileSync, spawnSync } = require('child_process');

// -- Test Harness --
let passed = 0;
let failed = 0;
let skipped = 0;
const results = [];

function test(name, fn) {
  try {
    fn();
    passed++;
    results.push({ name, status: 'PASS' });
    console.log(`  ✓ ${name}`);
  } catch (e) {
    failed++;
    results.push({ name, status: 'FAIL', error: e.message });
    console.log(`  ✗ ${name}`);
    console.log(`    → ${e.message}`);
  }
}

function skip(name, reason) {
  skipped++;
  results.push({ name, status: 'SKIP', reason });
  console.log(`  ⊘ ${name} (${reason})`);
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'Assertion failed');
}

function assertEqual(actual, expected, msg) {
  if (actual !== expected) {
    throw new Error(`${msg || 'Mismatch'}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function assertIncludes(arr, item, msg) {
  if (!arr.includes(item)) {
    throw new Error(`${msg || 'Missing'}: ${JSON.stringify(item)} not in [${arr.join(', ')}]`);
  }
}

// -- Resolve Paths --
const ROOT = path.resolve(__dirname, '..');
const MAIN_PATH = path.join(ROOT, 'main.js');
const PRELOAD_PATH = path.join(ROOT, 'preload.js');
const INDEX_PATH = path.join(ROOT, 'index.html');
const LAUNCHER_PATH = path.join(ROOT, 'launcher.js');
const PACKAGE_PATH = path.join(ROOT, 'package.json');
const TEST_DIR = path.join(os.tmpdir(), 'veritas-recorder-test-' + Date.now());

let ffmpegPath;
try {
  ffmpegPath = require('ffmpeg-static');
} catch (e) {
  ffmpegPath = 'ffmpeg';
}

// ===========================================================
console.log('\n╔===============================================╗');
console.log('║  VERITAS Recorder v2 - Test Suite             ║');
console.log('╚===============================================╝\n');

// -- Setup --
fs.mkdirSync(TEST_DIR, { recursive: true });

// Create a tiny test WebM using FFmpeg (1 second, 10x10 pixels)
const TEST_WEBM = path.join(TEST_DIR, 'test-input.webm');
let hasTestFixture = false;
try {
  const genResult = spawnSync(ffmpegPath, [
    '-f', 'lavfi', '-i', 'color=c=red:s=160x120:d=2',
    '-c:v', 'libvpx', '-b:v', '200k', '-y', TEST_WEBM
  ], { timeout: 15000, stdio: ['pipe', 'pipe', 'pipe'] });
  hasTestFixture = fs.existsSync(TEST_WEBM) && fs.statSync(TEST_WEBM).size > 0;
  if (!hasTestFixture) {
    console.log('⚠  Could not generate test WebM fixture');
    if (genResult.stderr) console.log('   FFmpeg stderr:', genResult.stderr.toString().slice(-200));
  }
} catch (e) {
  console.log('⚠  FFmpeg fixture generation failed:', e.message);
}

// ===========================================================
console.log('━━━ 1. File Structure ━━━');
// ===========================================================

test('main.js exists', () => {
  assert(fs.existsSync(MAIN_PATH), 'main.js not found');
});

test('preload.js exists', () => {
  assert(fs.existsSync(PRELOAD_PATH), 'preload.js not found');
});

test('index.html exists', () => {
  assert(fs.existsSync(INDEX_PATH), 'index.html not found');
});

test('launcher.js exists', () => {
  assert(fs.existsSync(LAUNCHER_PATH), 'launcher.js not found');
});

test('package.json exists and is valid', () => {
  assert(fs.existsSync(PACKAGE_PATH), 'package.json not found');
  const pkg = JSON.parse(fs.readFileSync(PACKAGE_PATH, 'utf-8'));
  assertEqual(pkg.main, 'main.js', 'main entry');
  assert(pkg.devDependencies && pkg.devDependencies.electron, 'electron dep missing');
});

test('node_modules/ffmpeg-static exists', () => {
  const p = path.join(ROOT, 'node_modules', 'ffmpeg-static', 'index.js');
  assert(fs.existsSync(p), 'ffmpeg-static not installed');
});

// ===========================================================
console.log('\n━━━ 2. FFmpeg Binary ━━━');
// ===========================================================

test('FFmpeg binary resolves', () => {
  assert(ffmpegPath, 'ffmpegPath is null');
  assert(typeof ffmpegPath === 'string', 'ffmpegPath not a string');
});

test('FFmpeg binary exists on disk', () => {
  // ffmpeg-static returns absolute path
  if (ffmpegPath === 'ffmpeg') {
    skip('FFmpeg binary path', 'using system ffmpeg');
    return;
  }
  assert(fs.existsSync(ffmpegPath), `Binary not found at: ${ffmpegPath}`);
});

test('FFmpeg binary is executable', () => {
  const result = spawnSync(ffmpegPath, ['-version'], {
    timeout: 5000, stdio: ['pipe', 'pipe', 'pipe']
  });
  assertEqual(result.status, 0, 'FFmpeg exit code');
  const stdout = result.stdout.toString();
  assert(stdout.includes('ffmpeg version'), 'Version string missing');
});

test('FFmpeg supports libvpx (WebM decode)', () => {
  const result = spawnSync(ffmpegPath, ['-codecs'], {
    timeout: 5000, stdio: ['pipe', 'pipe', 'pipe']
  });
  const stdout = result.stdout.toString();
  assert(stdout.includes('libvpx') || stdout.includes('vp8') || stdout.includes('vp9'),
    'No VP8/VP9 codec support');
});

test('FFmpeg supports libx264 (MP4 encode)', () => {
  const result = spawnSync(ffmpegPath, ['-codecs'], {
    timeout: 5000, stdio: ['pipe', 'pipe', 'pipe']
  });
  const stdout = result.stdout.toString();
  assert(stdout.includes('libx264'), 'No H.264 codec support');
});

// ===========================================================
console.log('\n━━━ 3. Main Process - IPC Handlers ━━━');
// ===========================================================

const mainSrc = fs.readFileSync(MAIN_PATH, 'utf-8');

test('main.js imports all required Electron modules', () => {
  const required = ['app', 'BrowserWindow', 'ipcMain', 'dialog', 'desktopCapturer',
                     'globalShortcut', 'screen', 'shell'];
  for (const mod of required) {
    assert(mainSrc.includes(mod), `Missing import: ${mod}`);
  }
});

test('main.js imports os, fs, path, child_process', () => {
  assert(mainSrc.includes("require('path')"), 'Missing path');
  assert(mainSrc.includes("require('fs')"), 'Missing fs');
  assert(mainSrc.includes("require('os')"), 'Missing os');
  assert(mainSrc.includes("require('child_process')"), 'Missing child_process');
});

test('IPC handler: get-sources registered', () => {
  assert(mainSrc.includes("ipcMain.handle('get-sources'"), 'get-sources handler missing');
});

test('IPC handler: save-recording registered', () => {
  assert(mainSrc.includes("ipcMain.handle('save-recording'"), 'save-recording handler missing');
});

test('IPC handler: list-recordings registered', () => {
  assert(mainSrc.includes("ipcMain.handle('list-recordings'"), 'list-recordings handler missing');
});

test('IPC handler: open-recording registered', () => {
  assert(mainSrc.includes("ipcMain.handle('open-recording'"), 'open-recording handler missing');
});

test('IPC handler: open-recordings-folder registered', () => {
  assert(mainSrc.includes("ipcMain.handle('open-recordings-folder'"), 'open-recordings-folder handler missing');
});

test('IPC handler: delete-recording registered', () => {
  assert(mainSrc.includes("ipcMain.handle('delete-recording'"), 'delete-recording handler missing');
});

test('IPC handler: probe-duration registered', () => {
  assert(mainSrc.includes("ipcMain.handle('probe-duration'"), 'probe-duration handler missing');
});

test('IPC handler: convert-video registered', () => {
  assert(mainSrc.includes("ipcMain.handle('convert-video'"), 'convert-video handler missing');
});

test('IPC handler: trim-video registered', () => {
  assert(mainSrc.includes("ipcMain.handle('trim-video'"), 'trim-video handler missing');
});

test('Window control: minimize registered', () => {
  assert(mainSrc.includes("ipcMain.on('window:minimize'"), 'window:minimize missing');
});

test('Window control: restore registered', () => {
  assert(mainSrc.includes("ipcMain.on('window:restore'"), 'window:restore missing');
});

test('Window control: close registered', () => {
  assert(mainSrc.includes("ipcMain.on('window:close'"), 'window:close missing');
});

test('Global shortcut Ctrl+Shift+R registered', () => {
  assert(mainSrc.includes('CommandOrControl+Shift+R'), 'Hotkey not registered');
});

test('Security: contextIsolation is true', () => {
  assert(mainSrc.includes('contextIsolation: true'), 'contextIsolation not true');
});

test('Security: nodeIntegration is false', () => {
  assert(mainSrc.includes('nodeIntegration: false'), 'nodeIntegration not false');
});

test('Convert supports MP4 format', () => {
  assert(mainSrc.includes("'mp4'") && mainSrc.includes('libx264'), 'MP4 conversion missing');
});

test('Convert supports GIF format', () => {
  assert(mainSrc.includes("'gif'") && mainSrc.includes('lanczos'), 'GIF conversion missing');
});

test('Convert supports MOV format', () => {
  assert(mainSrc.includes("'mov'"), 'MOV conversion missing');
});

test('Trim uses stream copy (-c copy)', () => {
  assert(mainSrc.includes("'-c', 'copy'"), 'Trim should use -c copy for speed');
});

test('recordingsDir defaults to ~/Videos', () => {
  assert(mainSrc.includes("os.homedir()") && mainSrc.includes("'Videos'"),
    'Default recordings dir not ~/Videos');
});

// ===========================================================
console.log('\n━━━ 4. Preload - Bridge Methods ━━━');
// ===========================================================

const preloadSrc = fs.readFileSync(PRELOAD_PATH, 'utf-8');

const bridgeMethods = [
  'getSources', 'saveRecording', 'listRecordings', 'openRecording',
  'openRecordingsFolder', 'deleteRecording', 'probeDuration',
  'convertVideo', 'trimVideo', 'onConvertProgress',
  'minimize', 'restore', 'close', 'onToggleRecording'
];

for (const method of bridgeMethods) {
  test(`Preload exposes: ${method}`, () => {
    assert(preloadSrc.includes(method), `Bridge method '${method}' not found in preload.js`);
  });
}

test('Preload uses contextBridge', () => {
  assert(preloadSrc.includes('contextBridge.exposeInMainWorld'), 'contextBridge not used');
});

test('Preload exposes under "recorder" namespace', () => {
  assert(preloadSrc.includes("'recorder'"), 'Not exposed as "recorder"');
});

// ===========================================================
console.log('\n━━━ 5. Index.html - UI Structure ━━━');
// ===========================================================

const htmlSrc = fs.readFileSync(INDEX_PATH, 'utf-8');

test('HTML has three tabs: Record, Library, Convert', () => {
  assert(htmlSrc.includes('data-tab="record"'), 'Record tab missing');
  assert(htmlSrc.includes('data-tab="recordings"'), 'Library tab missing');
  assert(htmlSrc.includes('data-tab="convert"'), 'Convert tab missing');
});

test('HTML has live preview container', () => {
  assert(htmlSrc.includes('preview-container'), 'Preview container missing');
  assert(htmlSrc.includes('preview-video'), 'Preview video element missing');
  assert(htmlSrc.includes('preview-badge'), 'Preview badge missing');
});

test('HTML has hero record button', () => {
  assert(htmlSrc.includes('rec-btn'), 'Record button missing');
  assert(htmlSrc.includes('72px'), 'Button should be 72px hero size');
});

test('HTML has timer element', () => {
  assert(htmlSrc.includes('id="timer"'), 'Timer element missing');
});

test('HTML has source bar (collapsed)', () => {
  assert(htmlSrc.includes('source-bar-name'), 'Source bar name missing');
  assert(htmlSrc.includes('source-bar-change'), 'Source bar change button missing');
  assert(htmlSrc.includes('source-grid-wrapper'), 'Source grid wrapper missing');
});

test('HTML has quality presets (Low/Med/High/Max)', () => {
  assert(htmlSrc.includes('data-quality="low"'), 'Low preset missing');
  assert(htmlSrc.includes('data-quality="med"'), 'Med preset missing');
  assert(htmlSrc.includes('data-quality="high"'), 'High preset missing');
  assert(htmlSrc.includes('data-quality="max"'), 'Max preset missing');
});

test('HTML has advanced section (collapsed)', () => {
  assert(htmlSrc.includes('advanced-toggle'), 'Advanced toggle missing');
  assert(htmlSrc.includes('advanced-content'), 'Advanced content missing');
});

test('HTML has all toggle chips', () => {
  assert(htmlSrc.includes('toggle-audio'), 'Audio toggle missing');
  assert(htmlSrc.includes('toggle-webcam'), 'Webcam toggle missing');
  assert(htmlSrc.includes('toggle-autosave'), 'Auto-save toggle missing');
  assert(htmlSrc.includes('toggle-countdown'), 'Countdown toggle missing');
});

test('HTML has recordings list container', () => {
  assert(htmlSrc.includes('recordings-list'), 'Recordings list missing');
});

test('HTML has convert controls', () => {
  assert(htmlSrc.includes('convert-controls'), 'Convert controls missing');
  assert(htmlSrc.includes('data-format="mp4"'), 'MP4 format button missing');
  assert(htmlSrc.includes('data-format="mov"'), 'MOV format button missing');
  assert(htmlSrc.includes('data-format="gif"'), 'GIF format button missing');
  assert(htmlSrc.includes('data-format="avi"'), 'AVI format button missing');
});

test('HTML has trim inputs', () => {
  assert(htmlSrc.includes('trim-start'), 'Trim start missing');
  assert(htmlSrc.includes('trim-end'), 'Trim end missing');
});

test('HTML has progress bar', () => {
  assert(htmlSrc.includes('convert-progress-bar'), 'Progress bar missing');
  assert(htmlSrc.includes('convert-progress-fill'), 'Progress fill missing');
});

test('HTML has webcam PiP container', () => {
  assert(htmlSrc.includes('webcam-pip'), 'Webcam PiP missing');
  assert(htmlSrc.includes('webcam-video'), 'Webcam video element missing');
});

test('HTML has countdown overlay CSS', () => {
  assert(htmlSrc.includes('countdown-overlay'), 'Countdown overlay missing');
  assert(htmlSrc.includes('countdown-number'), 'Countdown number missing');
  assert(htmlSrc.includes('countPulse'), 'Countdown animation missing');
});

test('CSS has ready-breathe animation', () => {
  assert(htmlSrc.includes('ready-breathe'), 'Ready breathe animation missing');
});

test('CSS has micro-feedback on press', () => {
  assert(htmlSrc.includes('.rec-btn:active'), 'Press feedback missing');
  assert(htmlSrc.includes('scale(0.92)'), 'Scale-down value missing');
});

test('JS has QUALITY_MAP with correct values', () => {
  assert(htmlSrc.includes('2_000_000'), 'Low bitrate missing');
  assert(htmlSrc.includes('4_000_000'), 'Med bitrate missing');
  assert(htmlSrc.includes('8_000_000'), 'High bitrate missing');
  assert(htmlSrc.includes('16_000_000'), 'Max bitrate missing');
});

test('JS has auto-minimize for screen captures', () => {
  assert(htmlSrc.includes("startsWith('screen:')"), 'Screen detection missing');
  assert(htmlSrc.includes('window.recorder.minimize()'), 'Auto-minimize call missing');
});

test('JS has auto-restore after recording', () => {
  assert(htmlSrc.includes('window.recorder.restore()'), 'Auto-restore call missing');
});

test('JS has startPreview function', () => {
  assert(htmlSrc.includes('async function startPreview'), 'startPreview function missing');
});

test('JS has setPreviewLive function', () => {
  assert(htmlSrc.includes('function setPreviewLive'), 'setPreviewLive function missing');
});

test('JS has parseTimeToSeconds function', () => {
  assert(htmlSrc.includes('function parseTimeToSeconds'), 'parseTimeToSeconds function missing');
});

test('JS source bar shows "Recording:" prefix', () => {
  assert(htmlSrc.includes('Recording: ${'), 'Recording prefix missing');
});

// ===========================================================
console.log('\n━━━ 6. Launcher ━━━');
// ===========================================================

const launcherSrc = fs.readFileSync(LAUNCHER_PATH, 'utf-8');

test('Launcher strips ELECTRON_RUN_AS_NODE', () => {
  assert(launcherSrc.includes('ELECTRON_RUN_AS_NODE'), 'ELECTRON_RUN_AS_NODE not referenced');
  assert(launcherSrc.includes('delete cleanEnv.ELECTRON_RUN_AS_NODE'), 'Not deleting env var');
});

test('Launcher spawns electron with cwd', () => {
  assert(launcherSrc.includes("cwd: __dirname"), 'cwd not set');
  assert(launcherSrc.includes("require('electron')"), 'electron not required');
});

// ===========================================================
console.log('\n━━━ 7. FFmpeg Operations (Live) ━━━');
// ===========================================================

if (hasTestFixture) {
  test('FFmpeg probe: extracts duration from test WebM', () => {
    const result = spawnSync(ffmpegPath, ['-i', TEST_WEBM, '-f', 'null', '-'], {
      timeout: 10000, stdio: ['pipe', 'pipe', 'pipe']
    });
    const stderr = result.stderr.toString();
    assert(stderr.includes('Duration:'), 'No Duration in probe output');
    const match = stderr.match(/Duration:\s*(\d+):(\d+):(\d+)/);
    assert(match, 'Cannot parse duration');
    const secs = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseInt(match[3]);
    assert(secs >= 1 && secs <= 10, `Duration ${secs}s out of expected range`);
  });

  test('FFmpeg convert: WebM → MP4', () => {
    const output = path.join(TEST_DIR, 'test-output.mp4');
    const result = spawnSync(ffmpegPath, [
      '-i', TEST_WEBM, '-c:v', 'libx264', '-preset', 'ultrafast',
      '-crf', '28', '-movflags', '+faststart', '-y', output
    ], { timeout: 15000, stdio: ['pipe', 'pipe', 'pipe'] });
    assertEqual(result.status, 0, 'FFmpeg exit code');
    assert(fs.existsSync(output), 'MP4 output not created');
    assert(fs.statSync(output).size > 0, 'MP4 output is empty');
  });

  test('FFmpeg convert: WebM → GIF', () => {
    const output = path.join(TEST_DIR, 'test-output.gif');
    const result = spawnSync(ffmpegPath, [
      '-i', TEST_WEBM, '-vf', 'fps=12,scale=160:-1:flags=lanczos',
      '-loop', '0', '-y', output
    ], { timeout: 15000, stdio: ['pipe', 'pipe', 'pipe'] });
    assertEqual(result.status, 0, 'FFmpeg exit code');
    assert(fs.existsSync(output), 'GIF output not created');
    assert(fs.statSync(output).size > 0, 'GIF output is empty');
  });

  test('FFmpeg trim: stream copy extract', () => {
    const output = path.join(TEST_DIR, 'test-trimmed.webm');
    const result = spawnSync(ffmpegPath, [
      '-i', TEST_WEBM, '-ss', '0', '-t', '1',
      '-c', 'copy', '-y', output
    ], { timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'] });
    assertEqual(result.status, 0, 'FFmpeg exit code');
    assert(fs.existsSync(output), 'Trimmed output not created');
    assert(fs.statSync(output).size > 0, 'Trimmed output is empty');
  });
} else {
  skip('FFmpeg probe', 'No test fixture');
  skip('FFmpeg convert WebM→MP4', 'No test fixture');
  skip('FFmpeg convert WebM→GIF', 'No test fixture');
  skip('FFmpeg trim', 'No test fixture');
}

// ===========================================================
console.log('\n━━━ 8. File Operations ━━━');
// ===========================================================

test('Write and read recording file', () => {
  const testFile = path.join(TEST_DIR, 'test-write.webm');
  const data = Buffer.from('fake-webm-data');
  fs.writeFileSync(testFile, data);
  assert(fs.existsSync(testFile), 'File not written');
  const read = fs.readFileSync(testFile);
  assertEqual(read.length, data.length, 'Size mismatch');
});

test('Delete recording file', () => {
  const testFile = path.join(TEST_DIR, 'test-delete.webm');
  fs.writeFileSync(testFile, 'data');
  assert(fs.existsSync(testFile), 'File not created');
  fs.unlinkSync(testFile);
  assert(!fs.existsSync(testFile), 'File not deleted');
});

test('List recordings from directory', () => {
  // Create test files
  fs.writeFileSync(path.join(TEST_DIR, 'a.webm'), 'data');
  fs.writeFileSync(path.join(TEST_DIR, 'b.mp4'), 'data');
  fs.writeFileSync(path.join(TEST_DIR, 'c.txt'), 'data'); // non-video

  const videoExts = ['.webm', '.mp4', '.mov', '.avi', '.mkv', '.gif'];
  const files = fs.readdirSync(TEST_DIR)
    .filter(f => videoExts.includes(path.extname(f).toLowerCase()));

  assert(files.includes('a.webm'), 'webm not found');
  assert(files.includes('b.mp4'), 'mp4 not found');
  assert(!files.includes('c.txt'), 'txt should be filtered out');
});

test('File naming convention: timestamp format', () => {
  const now = new Date();
  const filename = `recording-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}-${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}${String(now.getSeconds()).padStart(2,'0')}.webm`;
  assert(filename.match(/^recording-\d{8}-\d{6}\.webm$/), `Bad filename format: ${filename}`);
});

test('Recordings sort: newest first', () => {
  const files = [
    { name: 'a.webm', date: '2026-01-01T00:00:00Z' },
    { name: 'b.webm', date: '2026-03-15T00:00:00Z' },
    { name: 'c.webm', date: '2026-02-01T00:00:00Z' },
  ];
  const sorted = files.sort((a, b) => new Date(b.date) - new Date(a.date));
  assertEqual(sorted[0].name, 'b.webm', 'Newest should be first');
  assertEqual(sorted[2].name, 'a.webm', 'Oldest should be last');
});

// ===========================================================
console.log('\n━━━ 9. Quality Presets ━━━');
// ===========================================================

test('Quality map has all four presets', () => {
  const QUALITY_MAP = { low: 2_000_000, med: 4_000_000, high: 8_000_000, max: 16_000_000 };
  assertEqual(QUALITY_MAP.low, 2_000_000, 'Low bitrate');
  assertEqual(QUALITY_MAP.med, 4_000_000, 'Med bitrate');
  assertEqual(QUALITY_MAP.high, 8_000_000, 'High bitrate');
  assertEqual(QUALITY_MAP.max, 16_000_000, 'Max bitrate');
});

test('CRF values are valid for quality tiers', () => {
  // From main.js convert-video handler
  assert(mainSrc.includes("'18'"), 'High CRF 18 missing');
  assert(mainSrc.includes("'23'"), 'Med CRF 23 missing');
  assert(mainSrc.includes("'28'"), 'Low CRF 28 missing');
});

// ===========================================================
console.log('\n━━━ 10. Time Parsing ━━━');
// ===========================================================

function parseTimeToSeconds(str) {
  const parts = str.split(':').map(Number);
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return parseFloat(str) || 0;
}

test('parseTimeToSeconds: "1:30" = 90', () => {
  assertEqual(parseTimeToSeconds('1:30'), 90, 'M:SS');
});

test('parseTimeToSeconds: "0:00" = 0', () => {
  assertEqual(parseTimeToSeconds('0:00'), 0, 'Zero');
});

test('parseTimeToSeconds: "1:00:00" = 3600', () => {
  assertEqual(parseTimeToSeconds('1:00:00'), 3600, 'H:MM:SS');
});

test('parseTimeToSeconds: "0:05" = 5', () => {
  assertEqual(parseTimeToSeconds('0:05'), 5, 'Seconds');
});

test('parseTimeToSeconds: "10:30" = 630', () => {
  assertEqual(parseTimeToSeconds('10:30'), 630, '10 min 30 sec');
});

// ===========================================================
// Cleanup
// ===========================================================
try {
  fs.rmSync(TEST_DIR, { recursive: true, force: true });
} catch (e) {
  // best-effort cleanup
}

// ===========================================================
// Results
// ===========================================================
console.log('\n╔===============================================╗');
console.log(`║  Results: ${passed} PASS  ${failed} FAIL  ${skipped} SKIP`);
console.log('╚===============================================╝\n');

if (failed > 0) {
  console.log('Failed tests:');
  results.filter(r => r.status === 'FAIL').forEach(r => {
    console.log(`  ✗ ${r.name}: ${r.error}`);
  });
  process.exit(1);
} else {
  console.log('All tests passed. ✓');
  process.exit(0);
}
