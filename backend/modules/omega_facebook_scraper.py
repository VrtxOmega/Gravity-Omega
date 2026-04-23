"""
omega_facebook_scraper.py — Chrome-Session Facebook Group Scraper
=================================================================
Zero setup required — reads cookies directly from your Chrome installation.
No login prompt. No manual export. Just run it.

USAGE:
  python omega_facebook_scraper.py --group <group_url> [options]

OPTIONS:
  --group        Facebook group URL (required unless using --find-groups)
  --query        Keyword filter (only grab matching posts)
  --limit        Max posts to collect (default: 100)
  --no-images    Skip image downloads
  --out-dir      Output folder (default: C:/GOLIATH_WORKSPACE/FB_EVIDENCE/)
  --find-groups  Search for relevant local groups by keyword
  --chrome-profile  Chrome profile dir (auto-detected if omitted)

EXAMPLES:
  # Scrape the Brown Water group, filter for manganese:
  python omega_facebook_scraper.py \\
    --group "https://www.facebook.com/groups/victimsbethaltobrownwater" \\
    --query manganese --limit 200

  # Find relevant local groups:
  python omega_facebook_scraper.py --find-groups "Bethalto water"
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import tempfile
import urllib.request
import urllib.parse
from base64 import b64decode
from datetime import datetime
from pathlib import Path

DEFAULT_OUTDIR = Path("C:/GOLIATH_WORKSPACE/FB_EVIDENCE")
COOKIES_FILE   = Path("C:/GOLIATH_WORKSPACE/FB_EVIDENCE/.fb_cookies.json")


# ── Chrome Cookie Extraction ─────────────────────────────────────────────────

def _find_chrome_profile() -> Path:
    """Auto-locate the Chrome Default profile on Windows."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome Beta/User Data/Default",
        Path(os.environ.get("APPDATA", "")).parent / "Local/Google/Chrome/User Data/Default",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise RuntimeError("Chrome profile not found. Pass --chrome-profile explicitly.")


def _get_chrome_encryption_key(profile_dir: Path) -> bytes:
    """Extract Chrome's AES key from Local State (DPAPI-wrapped)."""
    import win32crypt
    local_state_path = profile_dir.parent / "Local State"
    with open(local_state_path, "r", encoding="utf-8") as f:
        ls = json.load(f)
    enc_key = b64decode(ls["os_crypt"]["encrypted_key"])[5:]  # strip DPAPI prefix
    return win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]


def _decrypt_cookie_value(enc_value: bytes, key: bytes) -> str:
    """Decrypt a Chrome cookie value (AES-256-GCM or legacy DPAPI)."""
    try:
        from Crypto.Cipher import AES
        if enc_value[:3] == b"v10" or enc_value[:3] == b"v11":
            iv   = enc_value[3:15]
            data = enc_value[15:-16]
            tag  = enc_value[-16:]
            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            return cipher.decrypt_and_verify(data, tag).decode("utf-8")
    except Exception:
        pass
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        return ""


def _copy_locked_db(src: Path) -> Path:
    """
    Copy a file that another process has open (locked read-only by Chrome).
    Uses Windows API BackupRead via ctypes — instant, no subprocess.
    Falls back to robocopy if ctypes fails.
    """
    import ctypes
    import ctypes.wintypes as wt

    tmp_dir = Path(tempfile.mkdtemp())
    dst = tmp_dir / src.name

    # Try ctypes CopyFileW first — works on locked files opened without FILE_SHARE_READ denied
    try:
        ok = ctypes.windll.kernel32.CopyFileW(str(src), str(dst), False)
        if ok and dst.exists():
            return dst
    except Exception:
        pass

    # Fallback: PowerShell Copy-Item (faster than robocopy for single file)
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command",
             f'Copy-Item -Path "{src}" -Destination "{dst}" -ErrorAction Stop'],
            capture_output=True, timeout=10
        )
        if dst.exists():
            return dst
    except Exception:
        pass

    # Last resort: robocopy (with longer timeout)
    try:
        subprocess.run(
            ["robocopy", str(src.parent), str(tmp_dir), src.name,
             "/NJS", "/NJH", "/NDL", "/R:1", "/W:0"],
            capture_output=True, timeout=30
        )
        if dst.exists():
            return dst
    except Exception:
        pass

    raise RuntimeError(
        f"Could not copy locked Chrome DB: {src}\n"
        "Close Chrome and try again, or run: python omega_facebook_scraper.py --chrome-profile <profile>"
    )


def extract_chrome_cookies(profile_dir: Path = None) -> list:
    """
    Load saved Facebook cookies.
    Order of preference:
      1. Saved JSON file (.fb_cookies.json) — from one-time setup
      2. Chrome Cookies DB (DPAPI decrypt — requires Chrome to be closed)
    """
    # 1. Saved cookies file (preferred)
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        print(f"Loaded {len(cookies)} cookies from saved file")
        return cookies

    # 2. Chrome DB path (fallback — often fails while Chrome is running)
    if profile_dir is None:
        profile_dir = _find_chrome_profile()

    try:
        key = _get_chrome_encryption_key(profile_dir)
    except ImportError:
        print("[!] pywin32 not installed — trying without decryption")
        key = None

    cookies_db = profile_dir / "Network" / "Cookies"
    if not cookies_db.exists():
        cookies_db = profile_dir / "Cookies"
    if not cookies_db.exists():
        raise FileNotFoundError(f"Chrome cookies DB not found at {profile_dir}")

    # Use Windows API / PowerShell to copy while Chrome holds the file lock
    tmp_db = _copy_locked_db(cookies_db)

    pw_cookies = []
    try:
        con = sqlite3.connect(str(tmp_db))
        cur = con.cursor()
        cur.execute("""
            SELECT host_key, name, encrypted_value, path,
                   expires_utc, is_secure, is_httponly, samesite
            FROM cookies
            WHERE host_key LIKE '%facebook.com%'
               OR host_key LIKE '%fbcdn.net%'
        """)
        for row in cur.fetchall():
            host, name, enc_val, path, expires, secure, httponly, samesite = row
            value = ""
            if key and enc_val:
                value = _decrypt_cookie_value(enc_val, key)

            # Convert Chrome epoch (microseconds since 1601) to Unix timestamp
            unix_exp = 0
            if expires and expires > 0:
                unix_exp = (expires / 1_000_000) - 11644473600

            sm_map = {-1: "Lax", 0: "None", 1: "Lax", 2: "Strict"}
            pw_cookies.append({
                "name":     name,
                "value":    value,
                "domain":   host if host.startswith(".") else f".{host}",
                "path":     path or "/",
                "expires":  unix_exp,
                "httpOnly": bool(httponly),
                "secure":   bool(secure),
                "sameSite": sm_map.get(samesite, "Lax"),
            })
        con.close()
    finally:
        tmp_db.unlink(missing_ok=True)

    print(f"Loaded {len(pw_cookies)} Facebook cookies from Chrome profile")
    return pw_cookies


# ── Scraper Core ─────────────────────────────────────────────────────────────

def _slug(url: str) -> str:
    m = re.search(r'groups/([^/?#]+)', url)
    return m.group(1) if m else re.sub(r'[^a-zA-Z0-9_-]', '_', url[-40:])


def _download_image(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer":    "https://www.facebook.com/",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            dest.write_bytes(r.read())
        return True
    except Exception:
        return False


def _dismiss_popups(page):
    for sel in [
        '[aria-label="Close"]',
        'div[role="dialog"] button[aria-label="Close"]',
        '[data-testid="cookie-policy-dialog-accept-button"]',
        'button:has-text("Accept All")',
        'button:has-text("Allow essential")',
    ]:
        try:
            page.locator(sel).first.click(timeout=1500)
            time.sleep(0.5)
        except Exception:
            pass


def scrape_group(
    group_url: str,
    query: str = None,
    limit: int = 100,
    download_images: bool = True,
    out_dir: Path = DEFAULT_OUTDIR,
    chrome_profile: Path = None,
) -> dict:
    from playwright.sync_api import sync_playwright

    # Try cookie extraction — if it fails, we'll use profile launch below
    cookies = None
    try:
        cookies = extract_chrome_cookies(chrome_profile)
    except Exception as e:
        print(f"[!] Cookie extraction failed ({e}) — will use profile launch")

    slug    = _slug(group_url)
    gdir    = out_dir / slug
    idir    = gdir / "images"
    gdir.mkdir(parents=True, exist_ok=True)
    if download_images:
        idir.mkdir(parents=True, exist_ok=True)

    posts      = []
    seen       = set()

    print(f"\n{'═'*60}")
    print(f" Group : {group_url}")
    print(f" Filter: {query or 'none'}")
    print(f" Limit : {limit}")
    print(f" Out   : {gdir}")
    print(f"{'═'*60}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/122.0.0.0 Safari/537.36")

        if cookies:
            # Cookie injection path (Chrome may be closed, or robocopy succeeded)
            ctx = browser.new_context(
                user_agent=ua,
                viewport={"width": 1280, "height": 900},
            )
            ctx.add_cookies(cookies)
        else:
            # Profile clone path — copy Chrome profile to temp, launch against it
            # This works while Chrome is running because we copy first
            src_profile = chrome_profile or _find_chrome_profile()
            tmp_profile = Path(tempfile.mkdtemp()) / "chrome_profile"
            print(f"  Cloning profile: {src_profile} → {tmp_profile}")
            subprocess.run(
                ["powershell.exe", "-Command",
                 f'Copy-Item -Path "{src_profile}" -Destination "{tmp_profile}" '
                 f'-Recurse -Force -Exclude "GPUCache","ShaderCache" '
                 f'-ErrorAction SilentlyContinue'],
                capture_output=True, timeout=60
            )
            browser.close()
            ctx = p.chromium.launch_persistent_context(
                str(tmp_profile),
                headless=True,
                user_agent=ua,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = ctx.new_page()
            # Wait for full network idle so React hydrates before we scrape
            page.goto(group_url, wait_until="load", timeout=30000)
            time.sleep(3)
            _dismiss_popups(page)
            # Wait for actual feed content to appear
            for wait_sel in ['[role="feed"]', '[data-pagelet^="FeedUnit"]',
                              'div[role="article"]', 'div[dir="auto"]']:
                try:
                    page.wait_for_selector(wait_sel, timeout=15000)
                    print(f"  Feed detected via: {wait_sel}")
                    break
                except Exception:
                    continue
            time.sleep(1)
            skip_goto = True

        if cookies:
            skip_goto = False

        if not skip_goto:
            page = ctx.new_page()
            page.goto(group_url, wait_until="load", timeout=30000)
            time.sleep(3)
            _dismiss_popups(page)
            for wait_sel in ['[role="feed"]', '[data-pagelet^="FeedUnit"]',
                              'div[role="article"]', 'div[dir="auto"]']:
                try:
                    page.wait_for_selector(wait_sel, timeout=15000)
                    print(f"  Feed detected via: {wait_sel}")
                    break
                except Exception:
                    continue
            time.sleep(1)

        stall = 0
        prev_h = 0
        seen_fp: set = set()

        EXTRACT_JS = """
        () => {
            const results = [];
            // Try li[role=listitem] first, fallback to div[role=article]
            let nodes = Array.from(document.querySelectorAll('li[role="listitem"]'));
            if (!nodes.length) {
                nodes = Array.from(document.querySelectorAll('div[role="article"]'));
            }

            for (const node of nodes) {
                // Text: collect all span/div[dir=auto] text, filter noise
                const parts = Array.from(
                    node.querySelectorAll('span[dir="auto"], div[dir="auto"]')
                ).map(el => el.innerText.trim()).filter(t => t.length > 15);
                const text = parts.join(' ').trim();
                if (!text || text.length < 20) continue;

                // Author: first <a role=link> with reasonable text length
                let author = '';
                for (const a of node.querySelectorAll('a[role="link"]')) {
                    const t = a.innerText.trim();
                    if (t && t.length > 2 && t.length < 80 && !t.includes('\\n')) {
                        author = t; break;
                    }
                }

                // Date: abbr data-utime title, or aria-label with time units
                let date_text = '';
                const abbr = node.querySelector('abbr[data-utime]');
                if (abbr) {
                    date_text = abbr.getAttribute('title') || abbr.innerText || '';
                } else {
                    const timed = node.querySelector(
                        '[aria-label*="hr"],[aria-label*="min"],[aria-label*="day"],' +
                        '[aria-label*="week"],[aria-label*="month"],[aria-label*="year"]'
                    );
                    if (timed) date_text = timed.getAttribute('aria-label') || '';
                }

                // Post URL
                let post_url = '';
                for (const a of node.querySelectorAll('a[href]')) {
                    const h = a.getAttribute('href') || '';
                    if (h.includes('/posts/') || h.includes('/permalink/')) {
                        post_url = h.startsWith('/') ? 'https://www.facebook.com' + h : h;
                        break;
                    }
                }

                // Images
                const img_srcs = Array.from(
                    node.querySelectorAll('img[src*="fbcdn"]')
                ).map(i => i.getAttribute('src')).filter(s => s && !s.includes('emoji'));

                results.push({ text, author, date_text, post_url, img_srcs });
            }
            return results;
        }
        """

        while len(posts) < limit and stall < 12:
            raw_posts = page.evaluate(EXTRACT_JS)
            for rp in raw_posts:
                if len(posts) >= limit:
                    break
                text = rp.get("text", "").strip()
                if not text or len(text) < 20:
                    continue
                # Keyword filter
                if query and query.lower() not in text.lower():
                    continue
                fp = text[:100]
                if fp in seen_fp:
                    continue
                seen_fp.add(fp)

                # Download images if requested
                imgs = []
                if download_images:
                    for i, src in enumerate(rp.get("img_srcs", [])[:5]):
                        dest = idir / f"post{len(posts):04d}_img{i}.jpg"
                        if _download_image(src, dest):
                            imgs.append(str(dest))

                author    = rp.get("author", "")
                date_text = rp.get("date_text", "")
                post_url  = rp.get("post_url", "")

                posts.append({
                    "index":     len(posts),
                    "author":    author,
                    "date_text": date_text,
                    "text":      text,
                    "images":    imgs,
                    "post_url":  post_url,
                })
                print(
                    f"  [{len(posts):3d}] "
                    f"{author[:25]:25s} | "
                    f"{date_text[:18]:18s} | "
                    f"{text[:55]}..."
                )

            # Scroll
            page.keyboard.press("End")
            time.sleep(2.5)
            new_h = page.evaluate("document.body.scrollHeight")
            if new_h == prev_h:
                stall += 1
            else:
                stall = 0
            prev_h = new_h

        browser.close()

    ts  = datetime.now().strftime("%Y%m%d_%H%M")
    out = gdir / f"scrape_{ts}.json"
    result = {
        "group_url":  group_url,
        "query":      query,
        "scraped_at": datetime.now().isoformat(),
        "post_count": len(posts),
        "posts":      posts,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(posts)} posts saved → {out}")
    return result


def find_groups(keyword: str, limit: int = 20, chrome_profile: Path = None) -> list:
    """Search Facebook for groups matching a keyword. Returns list of groups."""
    from playwright.sync_api import sync_playwright

    cookies = extract_chrome_cookies(chrome_profile)
    groups  = []

    url = f"https://www.facebook.com/groups/search/?q={urllib.parse.quote_plus(keyword)}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ))
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(3)
        _dismiss_popups(page)
        time.sleep(1)

        for card in page.locator('a[href*="/groups/"]').all()[:limit]:
            try:
                href = card.get_attribute("href") or ""
                name = card.inner_text(timeout=500).strip()
                if href and "groups" in href and name:
                    full = ("https://www.facebook.com" + href
                            if href.startswith("/") else href)
                    if full not in [g["url"] for g in groups]:
                        groups.append({"name": name, "url": full})
                        print(f"  Found: {name[:60]} → {full}")
            except Exception:
                continue

        browser.close()

    return groups


# ── Omega Module Entry Point ─────────────────────────────────────────────────

import urllib.parse

def omega_entry(**kwargs):
    """Called by the Omega Sovereign Module system."""
    action = kwargs.get("action", "scrape")
    if action == "find_groups":
        return find_groups(
            keyword=kwargs.get("query", "Bethalto water"),
            limit=int(kwargs.get("limit", 20)),
        )
    group_url = kwargs.get("group_url", "")
    if not group_url:
        return {"error": "group_url is required"}
    return scrape_group(
        group_url=group_url,
        query=kwargs.get("query"),
        limit=int(kwargs.get("limit", 100)),
        download_images=kwargs.get("images", True),
    )


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Omega Facebook Group Scraper — uses your Chrome session"
    )
    ap.add_argument("--group",          help="Facebook group URL to scrape")
    ap.add_argument("--query",          help="Keyword filter")
    ap.add_argument("--limit",          type=int, default=100)
    ap.add_argument("--no-images",      action="store_true")
    ap.add_argument("--out-dir",        default=str(DEFAULT_OUTDIR))
    ap.add_argument("--find-groups",    metavar="KEYWORD",
                    help="Search Facebook for groups matching keyword")
    ap.add_argument("--chrome-profile", help="Path to Chrome profile dir (auto-detected)")
    args = ap.parse_args()

    profile = Path(args.chrome_profile) if args.chrome_profile else None

    if args.find_groups:
        results = find_groups(args.find_groups, chrome_profile=profile)
        print(f"\nFound {len(results)} groups:")
        for g in results:
            print(f"  {g['name']}")
            print(f"    {g['url']}")
    elif args.group:
        scrape_group(
            group_url=args.group,
            query=args.query,
            limit=args.limit,
            download_images=not args.no_images,
            out_dir=Path(args.out_dir),
            chrome_profile=profile,
        )
    else:
        ap.print_help()
