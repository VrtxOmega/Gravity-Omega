import sys
sys.path.insert(0, 'backend/modules')
from omega_facebook_scraper import extract_chrome_cookies

try:
    cookies = extract_chrome_cookies()
    fb = [c for c in cookies if 'facebook' in c.get('domain', '')]
    print(f"Total cookies loaded: {len(cookies)}")
    print(f"Facebook cookies: {len(fb)}")
    session = [c for c in fb if c['name'] in ('c_user', 'xs', 'datr', 'fr')]
    print(f"Session tokens found: {[c['name'] for c in session]}")
    if len(session) >= 2:
        print("STATUS: READY - authenticated session detected")
    else:
        print("STATUS: WARN - may not be fully authenticated")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
