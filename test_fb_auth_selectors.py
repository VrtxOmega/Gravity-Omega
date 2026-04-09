"""
Dump authenticated Facebook group HTML to find real selectors.
Uses saved cookies from .fb_cookies.json
"""
import json, time, sys
from pathlib import Path
sys.path.insert(0, 'backend/modules')
from omega_facebook_scraper import COOKIES_FILE, _dismiss_popups

GROUP = "https://www.facebook.com/groups/victimsofbethaltosbrownwater"
cookies = json.loads(COOKIES_FILE.read_text())
print(f"Loaded {len(cookies)} cookies")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
    )
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    print(f"Loading group...")
    page.goto(GROUP, wait_until="load", timeout=30000)
    time.sleep(5)
    _dismiss_popups(page)
    time.sleep(2)
    page.keyboard.press("End"); time.sleep(3)
    page.keyboard.press("End"); time.sleep(3)

    print(f"Title: {page.title()}")
    print(f"URL:   {page.url}")

    html = page.content()
    out = Path("C:/GOLIATH_WORKSPACE/FB_EVIDENCE/fb_auth_dump.html")
    out.write_text(html, encoding="utf-8")
    print(f"HTML saved: {len(html)} chars → {out}")

    # Test every selector
    tests = [
        'div[role="feed"]',
        'div[role="article"]',
        '[data-pagelet^="FeedUnit"]',
        'div[dir="auto"]',
        'span[dir="auto"]',
        'div[data-ad-comet-preview]',
        'div[data-ad-preview]',
        'div[aria-posinset]',
        'div[data-virtualized]',
        'div[tabindex="0"]',
        'h2',
        'strong',
        'a[href*="/posts/"]',
        'a[href*="/groups/"][href*="/permalink/"]',
        'div[class*="userContent"]',
        '[data-testid="post_message"]',
    ]
    print("\n--- Selector Results ---")
    for sel in tests:
        try:
            n = page.locator(sel).count()
            marker = " ✓" if n > 0 else ""
            print(f"  {sel!r:55s} → {n}{marker}")
            if 0 < n < 5:
                for i in range(min(n, 2)):
                    try:
                        txt = page.locator(sel).nth(i).inner_text(timeout=500)[:80]
                        print(f"    [{i}] {txt!r}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"  {sel!r:55s} → ERR: {e}")
    browser.close()
