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
