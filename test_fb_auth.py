"""
Test suite for omega_facebook_scraper.
Tests:
  1. Profile clone path — verifies Playwright can auth via cloned Chrome profile
  2. Basic Facebook group page load — verifies we land on an authenticated page
"""
import sys
import time
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, 'backend/modules')
from omega_facebook_scraper import _find_chrome_profile, _dismiss_popups

def test_profile_clone_auth():
    """Clone Chrome profile and verify Facebook considers us logged in."""
    from playwright.sync_api import sync_playwright

    src_profile = _find_chrome_profile()
    tmp_profile = Path(tempfile.mkdtemp()) / "fb_test_profile"
    print(f"Cloning: {src_profile}")
    print(f"     To: {tmp_profile}")

    result = subprocess.run(
        ["powershell.exe", "-Command",
         f'Copy-Item -Path "{src_profile}" -Destination "{tmp_profile}" -Recurse -Force '
         f'-Exclude "GPUCache","ShaderCache","Code Cache","*.log" '
         f'-ErrorAction SilentlyContinue'],
        capture_output=True, timeout=60
    )
    print(f"Clone exit: {result.returncode}")

    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/122.0.0.0 Safari/537.36")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(tmp_profile),
            headless=True,
            user_agent=ua,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        print("Navigating to Facebook...")
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        _dismiss_popups(page)

        title = page.title()
        url   = page.url
        # If we're logged in, Facebook shows "Facebook" or your name — not "Log in"
        logged_in = "log in" not in title.lower() and "login" not in url.lower()
        print(f"Title: {title}")
        print(f"URL  : {url}")
        print(f"STATUS: {'AUTHENTICATED ✓' if logged_in else 'NOT LOGGED IN ✗'}")
        ctx.close()
        return logged_in

if __name__ == "__main__":
    ok = test_profile_clone_auth()
    sys.exit(0 if ok else 1)
