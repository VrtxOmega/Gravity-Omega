"""
Targeted debug: profile clone then load FB group, capture any errors verbosely.
"""
import sys, subprocess, tempfile, time, traceback
from pathlib import Path

sys.path.insert(0, 'backend/modules')
from omega_facebook_scraper import _find_chrome_profile, _dismiss_popups

src_profile = _find_chrome_profile()
tmp_profile = Path(tempfile.mkdtemp()) / "fb_debug_profile"

print(f"Cloning {src_profile} → {tmp_profile}")
r = subprocess.run(
    ["powershell.exe", "-Command",
     f'Copy-Item -Path "{src_profile}" -Destination "{tmp_profile}" '
     f'-Recurse -Force -Exclude "GPUCache","ShaderCache" -ErrorAction SilentlyContinue'],
    capture_output=True, timeout=60
)
print(f"Clone done. exit={r.returncode}")

ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

GROUP = "https://www.facebook.com/groups/victimsofbethaltosbrownwater"

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print("Launching persistent context...")
        ctx = p.chromium.launch_persistent_context(
            str(tmp_profile),
            headless=True,
            user_agent=ua,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        print(f"Navigating to {GROUP}")
        page.goto(GROUP, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)
        _dismiss_popups(page)
        print(f"Title: {page.title()}")
        print(f"URL:   {page.url}")

        # Try to find ANY post-like nodes
        for sel in [
            '[data-pagelet^="FeedUnit"]',
            'div[role="article"]',
            'div[data-testid="post_message"]',
            'div[dir="auto"]',
        ]:
            nodes = page.locator(sel).all()
            if nodes:
                print(f"Selector '{sel}' → {len(nodes)} nodes found")
                # Print first node text
                try:
                    print(f"  First: {nodes[0].inner_text(timeout=2000)[:200]}")
                except Exception as e:
                    print(f"  First: error: {e}")
                break
        else:
            print("No post nodes matched any selector")
            # Dump page source snippet
            html = page.content()
            print(f"Page HTML (first 1000): {html[:1000]}")

        ctx.close()
except Exception as e:
    traceback.print_exc()
