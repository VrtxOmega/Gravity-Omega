import sys
sys.path.append('c:\\Veritas_Lab\\gravity-omega-v2\\backend\\modules')
sys.path.append('c:\\Veritas_Lab')
from morning_brief import gather_moltbook_activity
from datetime import datetime, timedelta
import traceback
import json

def test():
    since_dt = datetime.now() - timedelta(days=2)
    try:
        from moltbook_client import MoltbookClient
        client = MoltbookClient()
        recent = client.get_own_posts(limit=10)
        valid = []
        for p in recent:
            dt_str = p.get('created_at')
            if dt_str:
                from datetime import datetime as dt2
                p_dt = dt2.fromisoformat(dt_str.replace('Z', '+00:00')).replace(tzinfo=None)
                print(f"p_dt: {p_dt}, since_dt: {since_dt}, p_dt >= since_dt: {p_dt >= since_dt}")
                if p_dt >= since_dt:
                    valid.append(p)
        print("VALID LENGTH:", len(valid))
    except Exception as e:
        traceback.print_exc()

test()
