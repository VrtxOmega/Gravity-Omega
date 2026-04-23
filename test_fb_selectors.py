"""
Dump Facebook group page HTML after full load to identify real post selectors.
"""
import sys, subprocess, tempfile, time
from pathlib import Path

sys.path.insert(0, 'backend/modules')
from omega_facebook_scraper import _find_chrome_profile, _dismiss_popups

GROUP = "https://www.facebook.com/groups/victimsofbethaltosbrownwater"
ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

src_profile = _find_chrome_profile()
tmp_profile = Path(tempfile.mkdtemp()) / "fb_html_dump"
print("Cloning profile...")
subprocess.run(
    ["powershell.exe", "-Command",
     f'Copy-Item -Path "{src_profile}" -Destination "{tmp_profile}" '
     f'-Recurse -Force -Exclude "GPUCache","ShaderCache" -ErrorAction SilentlyContinue'],
    capture_output=True, timeout=60
)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(tmp_profile), headless=True, user_agent=ua,
        viewport={"width": 1366, "height": 768},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = ctx.new_page()
    print(f"Loading {GROUP}...")
    page.goto(GROUP, wait_until="networkidle", timeout=60000)
    time.sleep(5)
    _dismiss_popups(page)
    time.sleep(2)

    # Try to scroll once to trigger content load
    page.keyboard.press("End"); time.sleep(3)
    page.keyboard.press("End"); time.sleep(3)

    html = page.content()
    # Save full HTML
    out = Path("C:/GOLIATH_WORKSPACE/FB_EVIDENCE/fb_group_dump.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"HTML saved ({len(html)} chars) → {out}")

    # Test candidate selectors
    tests = [
        'div[role="feed"]',
        'div[role="article"]',
        '[data-pagelet^="FeedUnit"]',
        'div[dir="auto"]',
        'div[data-ad-comet-preview]',
        'span[dir="auto"]',
        'h2',  # post headers
        'a[role="link"]',
        'div[class*="x1yztbdb"]',  # FB internal class
    ]
    print("\n--- Selector Results ---")
    for sel in tests:
        try:
            count = page.locator(sel).count()
            print(f"  {sel!r:50s} → {count} matches")
            if count > 0 and count < 10:
                for i in range(min(count, 3)):
                    try:
                        txt = page.locator(sel).nth(i).inner_text(timeout=1000)[:80]
                        print(f"    [{i}] {txt!r}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"  {sel!r:50s} → ERROR: {e}")

    ctx.close()
