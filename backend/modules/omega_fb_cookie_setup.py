"""
omega_fb_cookie_setup.py — Facebook Cookie Setup (interactive, one-time)
=========================================================================
Opens a browser window. Log into Facebook. Press Enter. Done.

RUN ONCE:
  python backend\\modules\\omega_fb_cookie_setup.py
"""

import json
from pathlib import Path

COOKIES_FILE = Path("FB_EVIDENCE/.fb_cookies.json")

def setup():
    from playwright.sync_api import sync_playwright

    COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" Facebook Cookie Setup")
    print("=" * 60)
    print()
    print("A browser window is opening. Log into Facebook if needed.")
    print("When you see your News Feed or the group page, come back")
    print("here and press Enter.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.goto("https://www.facebook.com/login", timeout=30000)

        # Always wait for user — never auto-detect
        input("\nLog in to Facebook in the browser window, then press Enter here >>> ")

        # Let any post-login redirects (2FA, etc.) settle
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # 2FA redirect — that's fine, save what we have

        # Save cookies immediately — login is done at this point
        cookies    = ctx.cookies()
        fb_cookies = [c for c in cookies if "facebook" in c.get("domain", "")]
        session    = [c["name"] for c in fb_cookies if c["name"] in ("c_user", "xs")]

        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(fb_cookies, f, indent=2)

        print(f"\nSaved {len(fb_cookies)} cookies → {COOKIES_FILE}")

        if session:
            print(f"Session tokens confirmed: {session}")
        else:
            print("WARNING: c_user / xs missing — were you fully logged in?")

        browser.close()

    print()
    if session:
        print("SUCCESS. Run the scraper:")
        print("  python backend\\modules\\omega_facebook_scraper.py --group <url>")
    else:
        print("Re-run this script and log in fully before pressing Enter.")


if __name__ == "__main__":
    setup()

