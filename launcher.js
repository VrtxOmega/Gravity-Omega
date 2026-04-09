#!/usr/bin/env node
/**
 * Gravity Omega — Ghost Executive Launcher
 * Creates a uniquely named .exe so this app has its own Task Manager identity.
 */
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const APP_NAME = 'GravityOmega';
const electronDir = path.join(__dirname, 'node_modules', 'electron', 'dist');
const srcExe = path.join(electronDir, 'electron.exe');
const ghostExe = path.join(electronDir, `${APP_NAME}.exe`);

if (!fs.existsSync(ghostExe) || fs.statSync(srcExe).mtimeMs > fs.statSync(ghostExe).mtimeMs) {
    fs.copyFileSync(srcExe, ghostExe);
  try {
    const rcEdit = `${process.env.LOCALAPPDATA}\electron-builder\Cache\winCodeSign\winCodeSign-2.6.0\rcedit-x64.exe`;
    if (fs.existsSync(rcEdit)) require('child_process').execSync(`"${rcEdit}" "${ghostExe}" --set-version-string "ProductName" "${APP_NAME}" --set-version-string "FileDescription" "${APP_NAME}"`);
  } catch(e) {
    console.error(`[Ghost Launcher] Error fixing ghost executable metadata: ${e.message}`);
  }
  console.log(`[${APP_NAME}] Ghost executable created.`);
}

const cleanEnv = Object.assign({}, process.env);
delete cleanEnv.ELECTRON_RUN_AS_NODE;

const args = ['.'];
if (process.argv.includes('--dev')) args.unshift('--enable-logging', '--inspect');

console.log(`[${APP_NAME}] Launching...`);
const child = spawn(ghostExe, args, { cwd: __dirname, env: cleanEnv, stdio: 'inherit' });
child.on('close', (code) => process.exit(code || 0));
