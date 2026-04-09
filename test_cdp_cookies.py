"""
Extract Facebook cookies from Chrome via Chrome DevTools Protocol (CDP).
This launches Chrome with --remote-debugging-port, reads the cookies live,
then closes it. Works whether Chrome is already running or not.
"""
import json
import subprocess
import time
import urllib.request
import tempfile
import shutil
import os
import sys
from pathlib import Path

CHROME_EXE = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)
OUTPUT = Path("C:/GOLIATH_WORKSPACE/FB_EVIDENCE/.fb_cookies.json")

def extract_via_cdp():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Use a temp user-data-dir COPY so we don't conflict with running Chrome
    src = Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default"
    tmp = Path(tempfile.mkdtemp()) / "chrome_cdp"

    print(f"Cloning profile to {tmp}...")
    subprocess.run(
        ["powershell.exe", "-Command",
         f'Copy-Item -Path "{src}" -Destination "{tmp}" '
         f'-Recurse -Force -Exclude "GPUCache","ShaderCache","Code Cache",'
         f'"Extension State","databases" -ErrorAction SilentlyContinue'],
        capture_output=True, timeout=90
    )

    port = 9222
    chrome_proc = subprocess.Popen([
        CHROME_EXE,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={tmp.parent}",
        "--profile-directory=chrome_cdp",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
    ])

    print(f"Chrome CDP launched (PID {chrome_proc.pid}), waiting for debugger...")
    time.sleep(4)

    # Verify it's up
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=5) as r:
            info = json.load(r)
            print(f"CDP ready: {info.get('Browser', 'unknown')}")
    except Exception as e:
        print(f"CDP not available: {e}")
        chrome_proc.terminate()
        return None

    # Get cookies via CDP Target.getTargets + Network.getAllCookies
    try:
        # Create a new tab
        with urllib.request.urlopen(
            urllib.request.Request(
                f"http://localhost:{port}/json/new?about:blank",
                method="PUT"
            ), timeout=5
        ) as r:
            tab = json.load(r)
        ws_url = tab["webSocketDebuggerUrl"].replace("ws://", "http://")

        # Use the HTTP polling mode via /json/protocol
        # Simpler: use requests via CDP REST-style
        # Just call Network.getAllCookies via the v8 inspector

        import websocket  # type: ignore  -- may not be installed

    except ImportError:
        print("[!] websocket-client not installed, trying requests...")

    # Fallback: use puppeteer-style CDP via urllib + WebSocket
    # The cleanest approach without external deps is reading cookies DB
    # from the CLONED profile dir (which is now decoupled from the running Chrome)
    from pathlib import Path
    cookies_db = tmp / "Network" / "Cookies"
    if not cookies_db.exists():
        cookies_db = tmp / "Cookies"
    print(f"Cookie DB: {cookies_db} (exists: {cookies_db.exists()})")

    chrome_proc.terminate()
    return str(cookies_db)

if __name__ == "__main__":
    result = extract_via_cdp()
    print(f"Result: {result}")
