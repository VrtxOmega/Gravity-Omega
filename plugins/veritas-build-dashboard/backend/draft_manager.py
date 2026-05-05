import json
from pathlib import Path
from datetime import datetime

DRAFTS_DIR = Path(__file__).resolve().parent / "data" / "drafts"

class DraftManager:
    def __init__(self):
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def save_draft(self, content: str, title: str = "Untitled") -> str:
        """Save the current editor state as a draft."""
        draft_path = DRAFTS_DIR / "latest.json"
        
        draft = {
            "title": title,
            "content": content,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(draft, f, indent=2)
            
        return str(draft_path)
    
    def get_latest_draft(self) -> dict:
        """Return the latest draft."""
        draft_path = DRAFTS_DIR / "latest.json"
        if draft_path.exists():
            try:
                with open(draft_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

draft_manager = DraftManager()
