"""
Inline debug: load the FB group page with cookies, then run JS extraction and print raw results.
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
        viewport={"width": 1920, "height": 1080},
    )
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    print("Loading...")
    page.goto(GROUP, wait_until="load", timeout=30000)
    time.sleep(5)
    _dismiss_popups(page)
    time.sleep(2)
    page.keyboard.press("End"); time.sleep(3)

    print(f"Title: {page.title()}")
    print(f"URL: {page.url}")

    # How many li[role=listitem] does the JS see?
    count_li = page.evaluate("() => document.querySelectorAll('li[role=\"listitem\"]').length")
    count_art = page.evaluate("() => document.querySelectorAll('div[role=\"article\"]').length")
    count_span = page.evaluate("() => document.querySelectorAll('span[dir=\"auto\"]').length")
    print(f"\nli[role=listitem]: {count_li}")
    print(f"div[role=article]: {count_art}")
    print(f"span[dir=auto]:    {count_span}")

    if count_span > 0:
        # dump first 5 spans
        texts = page.evaluate("""
            () => Array.from(document.querySelectorAll('span[dir="auto"]'))
                .slice(0, 10)
                .map(s => s.innerText.trim())
                .filter(t => t.length > 5)
        """)
        print("\nFirst span[dir=auto] texts:")
        for t in texts:
            print(f"  {t!r}")

    # Try the full extraction JS
    raw = page.evaluate("""
        () => {
            let nodes = Array.from(document.querySelectorAll('li[role="listitem"]'));
            if (!nodes.length) nodes = Array.from(document.querySelectorAll('div[role="article"]'));
            return nodes.slice(0, 5).map(node => ({
                tag: node.tagName,
                innerTextLen: node.innerText.length,
                firstText: node.innerText.slice(0, 100),
                spanCount: node.querySelectorAll('span[dir="auto"]').length,
            }));
        }
    """)
    print(f"\nRaw node extraction ({len(raw)} nodes):")
    for r in raw:
        print(f"  tag={r['tag']} textLen={r['innerTextLen']} spans={r['spanCount']}")
        print(f"    first100: {r['firstText']!r}")

    browser.close()
