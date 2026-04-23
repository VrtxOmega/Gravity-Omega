"""
VERITAS Ω — Morning Briefing
==============================
Reads your Veritas Vault and produces a branded one-page PDF
telling you where you left off, what's open, and what moved.

Designed to be something you look forward to reading.

Usage:
    python morning_brief.py              → generate + open today's briefing
    python morning_brief.py --no-open    → generate without opening
    python morning_brief.py --date 2026-03-14  → briefing for a specific date
"""

import os
import sys
import json
import glob
import re
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
VAULT_DB = Path(os.environ.get('APPDATA', '')) / 'veritas-vault' / 'vault_data' / 'vault.db'
ANTIGRAVITY_ROOT = Path(os.environ.get('USERPROFILE', '')) / '.gemini' / 'antigravity'
BRAIN_DIR = ANTIGRAVITY_ROOT / 'brain'
KNOWLEDGE_DIR = ANTIGRAVITY_ROOT / 'knowledge'
CAPTURES_DIR = Path(os.environ.get('APPDATA', '')) / 'veritas-vault' / 'vault_data' / 'captures'
ONEDRIVE = Path(os.environ.get('OneDrive', os.path.expanduser('~')))
PDF_SCRIPT = ONEDRIVE / 'Desktop' / 'AI WorK' / 'veritas_pdf.py'
OUTPUT_DIR = ONEDRIVE / 'Desktop' / 'VERITAS_PDF_Output'


def connect_vault():
    """Open a read-only connection to the Vault DB."""
    if not VAULT_DB.exists():
        return None
    conn = sqlite3.connect(str(VAULT_DB))
    conn.row_factory = sqlite3.Row
    return conn


# ── Data Collection ────────────────────────────────────────────────

def get_recent_sessions(conn, since_ts):
    """Get documents modified since timestamp, grouped by topic."""
    rows = conn.execute(
        "SELECT type, title, topic, conversation_id, modified_at "
        "FROM documents WHERE modified_at > ? ORDER BY modified_at DESC",
        (since_ts,)
    ).fetchall()
    return rows


def get_action_items(conn):
    """Get open action items."""
    try:
        rows = conn.execute(
            "SELECT description, priority, status FROM action_items "
            "WHERE status != 'done' ORDER BY priority DESC"
        ).fetchall()
        return rows
    except Exception:
        return []


def get_recent_timeline(conn, since_ts, limit=20):
    """Get recent timeline events."""
    rows = conn.execute(
        "SELECT event, detail, timestamp FROM timeline "
        "WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
        (since_ts, limit)
    ).fetchall()
    return rows


def scan_open_tasks():
    """Read task.md files from all brain conversations for open/in-progress items."""
    if not BRAIN_DIR.exists():
        return []

    tasks = []
    for conv_dir in BRAIN_DIR.iterdir():
        if not conv_dir.is_dir() or conv_dir.name.startswith('.'):
            continue
        task_file = conv_dir / 'task.md'
        if not task_file.exists():
            continue
        try:
            content = task_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            heading = next((l.lstrip('#').strip() for l in lines if l.startswith('#')), 'Untitled')
            open_items = [l.strip()[6:].strip() for l in lines if l.strip().startswith('- [ ]')]
            in_progress = [l.strip()[6:].strip() for l in lines if l.strip().startswith('- [/]')]
            completed = [l.strip()[6:].strip() for l in lines if l.strip().startswith('- [x]')]
            if open_items or in_progress:
                mtime = task_file.stat().st_mtime
                tasks.append({
                    'heading': heading,
                    'open': open_items,
                    'in_progress': in_progress,
                    'completed': completed,
                    'mtime': mtime,
                })
        except Exception:
            continue

    return sorted(tasks, key=lambda t: t['mtime'], reverse=True)


def scan_recent_artifacts(since_dt):
    """Scan brain artifacts updated since a given datetime."""
    if not BRAIN_DIR.exists():
        return []

    results = []
    for conv_dir in BRAIN_DIR.iterdir():
        if not conv_dir.is_dir() or conv_dir.name.startswith('.'):
            continue
        for f in conv_dir.iterdir():
            if f.suffix == '.md' and not f.name.startswith('.') and f.name != 'task.md':
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime >= since_dt:
                        content = f.read_text(encoding='utf-8', errors='ignore')
                        heading = None
                        for line in content.split('\n'):
                            if line.startswith('# '):
                                heading = line[2:].strip()
                                break
                        results.append({
                            'file': f.name,
                            'heading': heading or f.stem.replace('_', ' ').title(),
                            'mtime': mtime,
                        })
                except Exception:
                    continue

    return sorted(results, key=lambda r: r['mtime'], reverse=True)


def scan_recent_captures(since_dt):
    """Scan ChatGPT/Gemini/Claude captures for recent sessions."""
    if not CAPTURES_DIR.exists():
        return []

    sessions = []
    for source_dir in CAPTURES_DIR.iterdir():
        if not source_dir.is_dir():
            continue
        source = source_dir.name
        scan_dirs = [source_dir]
        # Also check _archived subdirectories
        if source == '_archived':
            scan_dirs = [d for d in source_dir.iterdir() if d.is_dir()]

        for scan_dir in scan_dirs:
            for meta_file in scan_dir.glob('*.metadata.json'):
                try:
                    meta = json.loads(meta_file.read_text(encoding='utf-8'))
                    updated = meta.get('updatedAt', '')
                    if not updated:
                        continue
                    updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00')).replace(tzinfo=None)
                    if updated_dt >= since_dt:
                        # Parse title from filename: 2026-03-14T16-38-20_Google_Gemini.md.metadata.json
                        name = meta_file.name.replace('.metadata.json', '').replace('.md', '')
                        # Strip ISO timestamp prefix
                        import re
                        clean = re.sub(r'^\d{4}-\d{2}-\d{2}T[\d-]+_', '', name).replace('_', ' ')
                        sessions.append({
                            'source': source if source != '_archived' else scan_dir.name,
                            'title': clean or name,
                            'updated': updated_dt,
                            'summary': meta.get('summary', ''),
                        })
                except Exception:
                    continue

    # Deduplicate by title (keep latest)
    seen = {}
    for s in sorted(sessions, key=lambda x: x['updated'], reverse=True):
        key = s['title'].lower().strip()
        if key not in seen:
            seen[key] = s

    return list(seen.values())


def scan_knowledge_items():
    """Get KI titles and summaries for context."""
    if not KNOWLEDGE_DIR.exists():
        return []

    items = []
    for ki_dir in KNOWLEDGE_DIR.iterdir():
        if not ki_dir.is_dir():
            continue
        meta_file = ki_dir / 'metadata.json'
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding='utf-8'))
            items.append({
                'title': meta.get('title', ki_dir.name.replace('_', ' ').title()),
                'summary': meta.get('summary', ''),
            })
        except Exception:
            continue
    return items


def get_activity_streak():
    """Count consecutive days with brain artifacts."""
    if not BRAIN_DIR.exists():
        return 0

    # Collect all artifact modification dates
    dates = set()
    for conv_dir in BRAIN_DIR.iterdir():
        if not conv_dir.is_dir() or conv_dir.name.startswith('.'):
            continue
        for f in conv_dir.iterdir():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                dates.add(mtime.strftime('%Y-%m-%d'))
            except Exception:
                continue

    # Count streak backwards from today
    streak = 0
    d = datetime.now()
    while d.strftime('%Y-%m-%d') in dates:
        streak += 1
        d -= timedelta(days=1)
    return streak


# ── Human-Friendly Time ───────────────────────────────────────────

def human_time_ago(dt):
    """Convert a datetime to a friendly 'X hours ago' string."""
    now = datetime.now()
    diff = now - dt
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return "just now"
    elif hours < 2:
        return "about an hour ago"
    elif hours < 24:
        return f"{int(hours)} hours ago"
    else:
        days = int(hours / 24)
        return "yesterday" if days == 1 else f"{days} days ago"


def greeting():
    """Time-appropriate greeting with personal touch."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning, RJ"
    elif hour < 17:
        return "Good afternoon, RJ"
    else:
        return "Good evening, RJ"


def load_horizon():
    """Load upcoming events from horizon.json + auto-extract from vault action items."""
    items = []
    today = datetime.now().strftime('%Y-%m-%d')

    # 1. Manual entries from horizon.json
    horizon_path = Path(__file__).parent / 'horizon.json'
    if horizon_path.exists():
        try:
            data = json.loads(horizon_path.read_text(encoding='utf-8'))
            items.extend(data.get('items', []))
        except Exception:
            pass

    # 2. Auto-extract from vault action items containing date patterns
    conn = connect_vault()
    if conn:
        try:
            rows = conn.execute(
                "SELECT description FROM action_items WHERE status != 'done'"
            ).fetchall()
            date_pat = re.compile(r'(\d{4}-\d{2}-\d{2})')
            day_names = {'monday': 0, 'tuesday': 1, 'wednesday': 2,
                         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
            for row in rows:
                desc = row[0] if isinstance(row, (tuple, list)) else row['description']
                # Match explicit YYYY-MM-DD dates
                m = date_pat.search(desc)
                if m:
                    items.append({'date': m.group(1), 'label': desc})
                    continue
                # Match day names ("Wednesday", "Friday")
                desc_lower = desc.lower()
                for day_name, day_num in day_names.items():
                    if day_name in desc_lower:
                        now = datetime.now()
                        days_ahead = day_num - now.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        target = now + timedelta(days=days_ahead)
                        items.append({'date': target.strftime('%Y-%m-%d'), 'label': desc})
                        break
        except Exception:
            pass
        finally:
            conn.close()

    # Filter to future/today and deduplicate by label
    seen = set()
    upcoming = []
    for i in items:
        if i.get('date', '') >= today and i.get('label', '') not in seen:
            seen.add(i['label'])
            upcoming.append(i)
    return sorted(upcoming, key=lambda x: x.get('date', ''))


def compute_since_yesterday(recent_artifacts, recent_captures, open_tasks, since_24h):
    """Figure out what changed in the last 24 hours for the 'Since Yesterday' block."""
    new_artifacts = [a for a in recent_artifacts if a['mtime'] >= since_24h]
    new_captures = [c for c in recent_captures if c['updated'] >= since_24h]

    # Count recently completed items across all task.md files
    completed_recently = 0
    for task in open_tasks:
        completed_recently += len(task['completed'])

    return {
        'new_artifacts': new_artifacts,
        'new_captures': new_captures,
        'artifact_count': len(new_artifacts),
        'capture_count': len(new_captures),
        'completed_count': completed_recently,
    }


def derive_focus(action_items, in_progress_items, open_tasks):
    """Pick the single highest-priority thing to focus on today."""
    # 1. High-priority action items first
    high = [a for a in action_items if a['status'] == 'open' and a['priority'] in ('high', 'critical')]
    if high:
        return high[0]['description']

    # 2. In-progress work (you already started it — finish it)
    if in_progress_items:
        item, src = in_progress_items[0]
        return f"{item} (from {src})"

    # 3. First open item from the most recent task
    if open_tasks and open_tasks[0]['open']:
        return f"{open_tasks[0]['open'][0]} (from {open_tasks[0]['heading']})"

    return None


def streak_moment(streak):
    """Generate evolving, prominent streak copy."""
    if streak >= 60:
        return f"**{streak} days.** Two months of unbroken work. This isn't discipline anymore — it's who you are."
    elif streak >= 30:
        return f"**{streak} days straight.** You're not building momentum — you *are* momentum."
    elif streak >= 21:
        return f"**{streak} days.** Three weeks running. The habit is locked in."
    elif streak >= 14:
        return f"**{streak}-day streak.** Two solid weeks. You're in the zone."
    elif streak >= 7:
        return f"**{streak} days running.** A full week. The rhythm is real."
    elif streak >= 3:
        return f"**Day {streak}.** Building something. Don't stop now."
    elif streak == 2:
        return "**Day 2.** Back-to-back. Let's make it three."
    elif streak == 1:
        return "**Day 1.** Fresh start. Make it count."
    else:
        return "**You're back.** Let's get after it."


def gather_moltbook_activity(since_dt):
    """Fetch Moltbook posts made by Omega since the given timestamp."""
    import sys
    if "C:\\Veritas_Lab" not in sys.path:
        sys.path.append("C:\\Veritas_Lab")
    try:
        from moltbook_client import MoltbookClient
        client = MoltbookClient()
        recent = client.get_own_posts(limit=10)
        valid = []
        for p in recent:
            dt_str = p.get('created_at')
            if dt_str:
                from datetime import datetime
                p_dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if p_dt >= since_dt:
                    valid.append(p)
        return valid
    except Exception as e:
        return []

# ── Briefing Generator ────────────────────────────────────────────

def generate_briefing(target_date=None, auto_open=True):
    """Build the morning briefing markdown and convert to PDF."""
    now = datetime.now()
    today = target_date or now.strftime('%Y-%m-%d')
    today_dt = datetime.strptime(today, '%Y-%m-%d')
    since_24h = now - timedelta(hours=24)
    since_48h = now - timedelta(hours=48)

    # ── Collect all data ──────────────────────────────────────────

    conn = connect_vault()
    action_items = []
    vault_doc_count = 0
    if conn:
        try:
            action_items = get_action_items(conn)
            try:
                vault_doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            except Exception:
                vault_doc_count = 0
        finally:
            conn.close()

    open_tasks = scan_open_tasks()
    recent_artifacts = scan_recent_artifacts(since_48h)
    recent_captures = scan_recent_captures(since_48h)
    ki_count = len(scan_knowledge_items())
    streak = get_activity_streak()
    horizon = load_horizon()
    moltbook_posts = gather_moltbook_activity(since_48h)

    # Derived data
    in_progress_items = []
    for task in open_tasks[:5]:
        for item in task['in_progress'][:2]:
            in_progress_items.append((item, task['heading']))

    delta = compute_since_yesterday(recent_artifacts, recent_captures, open_tasks, since_24h)
    focus = derive_focus(action_items, in_progress_items, open_tasks)

    # ── Build the markdown ────────────────────────────────────────

    lines = []
    day_name = now.strftime('%A')

    # ── Header: personal, warm ────────────────────────────────────

    lines.append(f"# {greeting()} — here's your {day_name} brief.")
    lines.append("")
    lines.append(f"*{now.strftime('%B %d, %Y')} · {vault_doc_count:,} docs · {ki_count} KIs*")
    lines.append("")

    # ── Streak — standalone moment, right up top ──────────────────

    if streak > 0:
        lines.append(streak_moment(streak))
        lines.append("")

    # ── Today's Focus — one clear directive ───────────────────────

    if focus:
        lines.append("### Today's focus")
        lines.append("")
        lines.append(f"Based on your priorities and open work: **{focus}**")
        lines.append("")

    # ── Since Yesterday — what moved overnight ────────────────────

    moved = []
    if delta['artifact_count'] > 0:
        moved.append(f"{delta['artifact_count']} session{'s' if delta['artifact_count'] != 1 else ''} touched")
    if delta['capture_count'] > 0:
        moved.append(f"{delta['capture_count']} capture{'s' if delta['capture_count'] != 1 else ''} came in")
    if delta['completed_count'] > 0:
        moved.append(f"{delta['completed_count']} task{'s' if delta['completed_count'] != 1 else ''} completed across all projects")

    if moved:
        lines.append("### Since yesterday")
        lines.append("")
        lines.append(f"In the last 24 hours: {', '.join(moved)}.")
        if delta['new_captures']:
            cap_names = [c['title'] for c in delta['new_captures'][:3]]
            lines.append(f" New captures: {', '.join(f'**{n}**' for n in cap_names)}{'.' if len(cap_names) <= 3 else '...'}")
        if delta['new_artifacts']:
            art_names = [a['heading'] for a in delta['new_artifacts'][:3]]
            lines.append(f" Sessions: {', '.join(f'**{n}**' for n in art_names)}.")
        lines.append("")

    # ── Where you left off — narrative, not bullets ───────────────

    if recent_artifacts:
        latest = recent_artifacts[0]
        ago = human_time_ago(latest['mtime'])

        line = f"You were last working on **{latest['heading']}** ({ago})."
        if len(recent_artifacts) > 1:
            others = [a['heading'] for a in recent_artifacts[1:4]]
            if len(others) == 1:
                line += f" Before that: **{others[0]}**."
            else:
                last = others[-1]
                rest = ', '.join(f"**{o}**" for o in others[:-1])
                line += f" Before that: {rest}, and **{last}**."
        lines.append(line)
        lines.append("")
    elif recent_captures:
        latest = recent_captures[0]
        ago = human_time_ago(latest['updated'])
        lines.append(f"Your last active session was **{latest['title']}** on {latest['source'].capitalize()}, {ago}.")
        lines.append("")

    # ── Unfinished business ───────────────────────────────────────

    if in_progress_items:
        lines.append("### Unfinished business")
        lines.append("")
        if len(in_progress_items) == 1:
            item, src = in_progress_items[0]
            lines.append(f"You left **{item}** mid-stream (from {src}). That's probably where to pick up.")
        else:
            lines.append("A few things were mid-stream:")
            lines.append("")
            for item, src in in_progress_items[:4]:
                lines.append(f"- **{item}** ({src})")
        lines.append("")

    # ── Backlog (compact) ─────────────────────────────────────────

    total_open = sum(len(t['open']) for t in open_tasks)
    active_projects = [t for t in open_tasks if t['open'] or t['in_progress']]

    if active_projects and total_open > 0:
        lines.append("### The backlog")
        lines.append("")
        top = active_projects[:5]
        project_strs = []
        for t in top:
            done = len(t['completed'])
            total = done + len(t['open']) + len(t['in_progress'])
            project_strs.append(f"**{t['heading']}** ({done}/{total})" if total > 0 else f"**{t['heading']}**")

        lines.append(f"{len(active_projects)} active project{'s' if len(active_projects) > 1 else ''}, {total_open} open items. Most traction:")
        lines.append("")
        for ps in project_strs:
            lines.append(f"- {ps}")
        if len(active_projects) > 5:
            lines.append(f"- *...plus {len(active_projects) - 5} more*")
        lines.append("")

    # ── Flagged action items (high priority only) ─────────────────

    if action_items:
        open_actions = [a for a in action_items if a['status'] == 'open']
        high = [a for a in open_actions if a['priority'] in ('high', 'critical')]
        if high:
            lines.append("### Flagged")
            lines.append("")
            for a in high[:4]:
                lines.append(f"- {a['description']}")
            if len(open_actions) > len(high):
                lines.append(f"- *+{len(open_actions) - len(high)} normal-priority items in the vault*")
            lines.append("")

    # ── On the Horizon — upcoming dates ───────────────────────────

    if horizon:
        lines.append("### On the horizon")
        lines.append("")
        for item in horizon[:5]:
            try:
                d = datetime.strptime(item['date'], '%Y-%m-%d')
                diff = (d - now).days
                if diff == 0:
                    when = "**Today**"
                elif diff == 1:
                    when = "Tomorrow"
                elif diff < 7:
                    when = d.strftime('%A')
                else:
                    when = d.strftime('%b %d')
                lines.append(f"- {when} — {item['label']}")
            except Exception:
                lines.append(f"- {item.get('date', '?')} — {item.get('label', '?')}")
        lines.append("")

    # ── Moltbook Activity ─────────────────────────────────────────

    if moltbook_posts:
        lines.append("### Moltbook Intel")
        lines.append("")
        if len(moltbook_posts) == 1:
            lines.append("Your AI made **1 broadcast** to the hive today.")
        else:
            lines.append(f"Your AI made **{len(moltbook_posts)} broadcasts** to the hive today.")
        lines.append("")
        for p in moltbook_posts:
            title = p.get('title', 'Untitled')
            content = p.get('content', '').replace('\n', ' ')
            if len(content) > 120:
                content = content[:117] + '...'
            lines.append(f"- **{title}**: *{content}*")
        lines.append("")

    # ── Closing ───────────────────────────────────────────────────

    lines.append("> Let's build.")
    lines.append("")

    md_content = '\n'.join(lines)

    # Write temp markdown
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUTPUT_DIR / f'morning_brief_{today}.md'
    md_path.write_text(md_content, encoding='utf-8')

    # Convert to PDF
    cmd = [sys.executable, str(PDF_SCRIPT), str(md_path)]
    if not auto_open:
        cmd.append('--no-open')
    cmd.append('--no-timestamp')

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout.strip())
        try:
            md_path.unlink()
        except Exception:
            pass
    else:
        print(f"PDF generation failed: {result.stderr}")
        print(f"Markdown saved at: {md_path}")

    return md_content


# ── Weekly Rollup ─────────────────────────────────────────────────

def generate_weekly_rollup(auto_open=True):
    """Generate a Friday-style weekly rollup covering the past 7 days."""
    now = datetime.now()
    week_start = now - timedelta(days=7)
    today = now.strftime('%Y-%m-%d')

    # Collect data
    conn = connect_vault()
    vault_doc_count = 0
    action_items = []
    if conn:
        try:
            vault_doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            action_items = get_action_items(conn)
        finally:
            conn.close()

    all_tasks = scan_open_tasks()
    recent_artifacts = scan_recent_artifacts(week_start)
    recent_captures = scan_recent_captures(week_start)
    ki_count = len(scan_knowledge_items())
    streak = get_activity_streak()
    moltbook_posts = gather_moltbook_activity(week_start)

    total_completed = sum(len(t['completed']) for t in all_tasks)
    total_open = sum(len(t['open']) for t in all_tasks)
    total_in_progress = sum(len(t['in_progress']) for t in all_tasks)

    lines = []
    lines.append(f"# Week in Review — {now.strftime('%B %d, %Y')}")
    lines.append("")
    lines.append(f"*{vault_doc_count:,} docs · {ki_count} KIs · {streak}-day streak*")
    lines.append("")

    if streak > 0:
        lines.append(streak_moment(streak))
        lines.append("")

    # Sessions touched this week
    lines.append("### This week's sessions")
    lines.append("")
    if recent_artifacts:
        lines.append(f"You touched **{len(recent_artifacts)} session{'s' if len(recent_artifacts) != 1 else ''}** this week:")
        lines.append("")
        for a in recent_artifacts[:10]:
            ago = human_time_ago(a['mtime'])
            lines.append(f"- **{a['heading']}** ({ago})")
        if len(recent_artifacts) > 10:
            lines.append(f"- *...plus {len(recent_artifacts) - 10} more*")
        lines.append("")
    else:
        lines.append("No session artifacts from this week.")
        lines.append("")

    # Captures
    if recent_captures:
        lines.append("### Captures")
        lines.append("")
        sources = {}
        for cap in recent_captures:
            src = cap['source'].capitalize()
            sources[src] = sources.get(src, 0) + 1
        parts = [f"**{count}** from {src}" for src, count in sources.items()]
        lines.append(f"{len(recent_captures)} captures came in: {', '.join(parts)}.")
        lines.append("")

    # Progress summary
    lines.append("### Progress snapshot")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"| --- | --- |")
    lines.append(f"| Tasks completed (all time) | {total_completed} |")
    lines.append(f"| Currently in progress | {total_in_progress} |")
    lines.append(f"| Open items | {total_open} |")
    lines.append(f"| Sessions this week | {len(recent_artifacts)} |")
    lines.append(f"| Captures this week | {len(recent_captures)} |")
    lines.append("")

    # Active projects
    active = [t for t in all_tasks if t['open'] or t['in_progress']]
    if active:
        lines.append("### Active projects")
        lines.append("")
        for t in active[:8]:
            done = len(t['completed'])
            total = done + len(t['open']) + len(t['in_progress'])
            lines.append(f"- **{t['heading']}** ({done}/{total})")
        lines.append("")

    # Next week
    horizon = load_horizon()
    if horizon:
        lines.append("### Coming up")
        lines.append("")
        for item in horizon[:5]:
            try:
                d = datetime.strptime(item['date'], '%Y-%m-%d')
                lines.append(f"- {d.strftime('%A, %b %d')} — {item['label']}")
            except Exception:
                lines.append(f"- {item.get('date', '?')} — {item.get('label', '?')}")
        lines.append("")

    if moltbook_posts:
        lines.append("### Moltbook Intel")
        lines.append("")
        if len(moltbook_posts) == 1:
            lines.append("Your AI made **1 broadcast** this week.")
        else:
            lines.append(f"Your AI made **{len(moltbook_posts)} broadcasts** this week.")
        lines.append("")
        for p in moltbook_posts:
            title = p.get('title', 'Untitled')
            content = p.get('content', '').replace('\n', ' ')
            if len(content) > 120:
                content = content[:117] + '...'
            lines.append(f"- **{title}**: *{content}*")
        lines.append("")

    lines.append("> Keep building.")
    lines.append("")

    md_content = '\n'.join(lines)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUTPUT_DIR / f'weekly_rollup_{today}.md'
    md_path.write_text(md_content, encoding='utf-8')

    cmd = [sys.executable, str(PDF_SCRIPT), str(md_path)]
    if not auto_open:
        cmd.append('--no-open')
    cmd.append('--no-timestamp')

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout.strip())
        try:
            md_path.unlink()
        except Exception:
            pass
    else:
        print(f"PDF generation failed: {result.stderr}")
        print(f"Markdown saved at: {md_path}")

    return md_content


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VERITAS Ω — Morning Briefing')
    parser.add_argument('--no-open', action='store_true', help="Don't auto-open the PDF")
    parser.add_argument('--date', help='Generate briefing for a specific date (YYYY-MM-DD)')
    parser.add_argument('--weekly', action='store_true', help='Generate weekly rollup instead of daily brief')

    args = parser.parse_args()
    if args.weekly:
        generate_weekly_rollup(auto_open=not args.no_open)
    else:
        generate_briefing(target_date=args.date, auto_open=not args.no_open)
