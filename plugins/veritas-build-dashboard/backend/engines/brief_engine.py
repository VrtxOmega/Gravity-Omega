import sys
from datetime import datetime, timedelta
from pathlib import Path

def generate_daily_brief() -> str:
    """
    Connect to Moltbook and VERITAS Vault to generate the Daily Intelligence Brief.
    """
    try:
        # Add the external paths required for the integration
        sys.path.insert(0, "C:\\Veritas_Lab")
        sys.path.insert(0, "C:\\Veritas_Lab\\gravity-omega-v2\\backend\\modules")
        
        from morning_brief import gather_moltbook_activity
        
        since_48h = datetime.now() - timedelta(hours=48)
        posts = gather_moltbook_activity(since_48h)
        
        md = [
            f"# Daily Intelligence Rollup",
            f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## System Telemetry",
            "- **Status**: ACTIVE",
            "- **Observation Window**: Past 48 Hours",
            f"- **Signals Caught**: {len(posts)}",
            "",
            "## Autonomous Artifacts"
        ]
        
        if not posts:
            md.append("\n*No significant artifacts recorded in the observation window.*")
        
        for post in posts:
            title = post.get("title", "Untitled Signal")
            created_at = post.get("created_at", "")
            
            md.append(f"### {title}")
            if created_at:
                md.append(f"*{created_at}*")
                
            content = post.get("content", "")
            if content:
                md.append("")
                md.append(content)
            
            md.append("---")
            
        md.append("\n*End of Brief*")
        
        # Remove paths to prevent scope leakage
        sys.path.remove("C:\\Veritas_Lab")
        sys.path.remove("C:\\Veritas_Lab\\gravity-omega-v2\\backend\\modules")
        
        return "\n".join(md)
        
    except Exception as e:
        return f"# Briefing Error\n\nFailed to sync from Moltbook bridge:\n\n```text\n{str(e)}\n```"
