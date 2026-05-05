"""
VERITAS Docs — HTML Engine
============================
Renders a VeritasDocument to a self-contained, styled HTML file.
All CSS inlined, Google Fonts embedded via link, VERITAS design system.
Supports: collapsible sections, print-friendly media queries, dark mode.
"""

import os
import re
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import BrandPreset, VeritasDocument


def _escape(text: str) -> str:
    """HTML-escape text."""
    return (text.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))


def _inline(text: str) -> str:
    """Convert markdown inline formatting to HTML."""
    text = _escape(text)
    # Code spans first
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def _parse_to_html(md_text: str) -> str:
    """Convert markdown to HTML body content."""
    lines = md_text.split('\n')
    html_parts = []
    in_code = False
    code_buf = []
    code_lang = ''
    table_buf = []
    in_list = False
    i = 0

    def flush_table():
        nonlocal table_buf
        if not table_buf:
            return
        h = '<table><thead><tr>'
        for cell in table_buf[0]:
            h += f'<th>{_inline(cell)}</th>'
        h += '</tr></thead><tbody>'
        for row in table_buf[1:]:
            h += '<tr>'
            for cell in row:
                h += f'<td>{_inline(cell)}</td>'
            h += '</tr>'
        h += '</tbody></table>'
        html_parts.append(h)
        table_buf = []

    def flush_list():
        nonlocal in_list
        if in_list:
            html_parts.append('</ul>')
            in_list = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Code blocks
        if stripped.startswith('```'):
            if in_code:
                html_parts.append(f'<pre><code class="lang-{code_lang}">{"".join(code_buf)}</code></pre>')
                code_buf = []
                in_code = False
            else:
                flush_table()
                flush_list()
                code_lang = stripped[3:].strip() or 'text'
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(_escape(line) + '\n')
            i += 1
            continue

        if not stripped:
            flush_table()
            flush_list()
            i += 1
            continue

        # Table rows
        if '|' in stripped and stripped.startswith('|'):
            flush_list()
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                i += 1
                continue
            table_buf.append(cells)
            i += 1
            continue
        else:
            flush_table()

        # HR / page break
        if re.match(r'^---+$', stripped):
            flush_list()
            html_parts.append('<hr class="section-break">')
            i += 1
            continue

        # Headings
        if stripped.startswith('# ') and not stripped.startswith('## '):
            flush_list()
            html_parts.append(f'<h1>{_inline(stripped[2:].strip())}</h1>')
            i += 1
            continue
        if stripped.startswith('## '):
            flush_list()
            html_parts.append(f'<h2>{_inline(stripped[3:].strip())}</h2>')
            i += 1
            continue
        if stripped.startswith('### '):
            flush_list()
            html_parts.append(f'<h3>{_inline(stripped[4:].strip())}</h3>')
            i += 1
            continue
        if stripped.startswith('#### '):
            flush_list()
            html_parts.append(f'<h4>{_inline(stripped[5:].strip())}</h4>')
            i += 1
            continue

        # Blockquote
        if stripped.startswith('>'):
            flush_list()
            html_parts.append(f'<blockquote>{_inline(stripped[1:].strip())}</blockquote>')
            i += 1
            continue

        # Bullets
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_parts.append('<ul>')
                in_list = True
            html_parts.append(f'<li>{_inline(stripped[2:].strip())}</li>')
            i += 1
            continue
        else:
            flush_list()

        # Body text
        html_parts.append(f'<p>{_inline(stripped)}</p>')
        i += 1

    flush_table()
    flush_list()
    if code_buf:
        html_parts.append(f'<pre><code>{"".join(code_buf)}</code></pre>')

    return '\n'.join(html_parts)


def render(doc: VeritasDocument, brand: BrandPreset, output_path: Path) -> Path:
    """Render a VeritasDocument to a self-contained HTML file."""
    body_html = _parse_to_html(doc.content)
    gen_date = datetime.now().strftime('%B %d, %Y — %H:%M')
    conf_label = brand.confidentiality_label

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape(doc.title)} — VERITAS Docs</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --gold:{brand.gold};--gold-bright:{brand.gold_bright};--gold-dim:{brand.gold_dim};
  --bg:{brand.obsidian};--white:{brand.warm_white};--gray:#4a4030;
  --conf-color:{brand.confidentiality_color};
}}
body{{background:var(--bg);color:var(--white);font-family:'Share Tech Mono',monospace;font-size:13px;line-height:1.8;min-height:100vh;padding:0}}
.hero{{text-align:center;padding:60px 40px 40px;border-bottom:1px solid #2a1f08;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:700px;height:350px;background:radial-gradient(ellipse at 50% 0%,rgba(201,168,76,.1) 0%,transparent 65%);pointer-events:none}}
.omega{{font-family:'Orbitron',monospace;font-size:72px;font-weight:900;color:var(--gold);text-shadow:0 0 12px rgba(240,192,64,0.7),0 0 50px rgba(201,168,76,.4);line-height:1;margin-bottom:12px;position:relative;z-index:1}}
.brand{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:20px;letter-spacing:8px;color:var(--gold);text-transform:uppercase;position:relative;z-index:1}}
.doc-title{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:28px;color:var(--gold);margin-top:20px;position:relative;z-index:1}}
.doc-sub{{color:#AAAAAA;font-size:13px;margin-top:6px;position:relative;z-index:1}}
.doc-date{{color:#999;font-size:11px;margin-top:8px;position:relative;z-index:1}}
.conf-badge{{display:inline-block;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:10px;letter-spacing:3px;color:var(--conf-color);border:1px solid var(--conf-color);padding:3px 12px;margin-top:12px;position:relative;z-index:1}}
.content{{max-width:860px;margin:0 auto;padding:40px 24px}}
h1{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:22px;color:var(--gold);margin:32px 0 12px;letter-spacing:2px;border-bottom:1px solid var(--gold);padding-bottom:8px}}
h2{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:16px;color:var(--gold);margin:28px 0 10px;letter-spacing:2px;border-bottom:1px solid #2a1f08;padding-bottom:6px}}
h3{{font-family:'Rajdhani',sans-serif;font-weight:600;font-size:13px;color:#CCC;margin:20px 0 8px;letter-spacing:1px}}
h4{{font-family:'Rajdhani',sans-serif;font-weight:600;font-size:12px;color:#999;margin:16px 0 6px}}
p{{margin:8px 0;line-height:1.8}}
strong{{color:var(--white)}}
em{{color:#999;font-style:italic}}
a{{color:var(--gold);text-decoration:none;border-bottom:1px solid var(--gold-dim)}}
a:hover{{color:var(--gold-bright)}}
code{{font-family:'Share Tech Mono',monospace;background:#111;padding:2px 6px;border:1px solid #222;font-size:12px;color:var(--gold-dim)}}
pre{{background:#0d0d0d;border:1px solid #2a1f08;padding:16px;margin:12px 0;overflow-x:auto}}
pre code{{background:none;border:none;padding:0;color:#888;font-size:11px}}
blockquote{{border-left:3px solid var(--gold);padding:10px 16px;margin:12px 0;color:var(--gold-dim);background:rgba(201,168,76,.04);font-style:italic}}
ul{{margin:8px 0;padding-left:24px}}
li{{margin:4px 0;color:var(--white)}}
li::marker{{color:var(--gold)}}
table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:12px}}
th{{background:var(--gold);color:#0d0d0d;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:11px;letter-spacing:1px;text-align:left;padding:8px 10px;text-transform:uppercase}}
td{{padding:7px 10px;border-bottom:1px solid #1a1a1a;color:var(--white)}}
tr:nth-child(even) td{{background:#0a0a0a}}
tr:nth-child(odd) td{{background:#0d0d0d}}
hr.section-break{{border:none;border-top:1px solid #2a1f08;margin:28px 0}}
.motto{{text-align:center;padding:28px;border-top:1px solid var(--gold);margin-top:40px;font-style:italic;color:var(--gold-dim);font-size:12px}}
.footer{{text-align:center;padding:16px;font-family:'Rajdhani',sans-serif;font-size:10px;letter-spacing:4px;color:var(--gold-dim);text-transform:uppercase}}
.footer span{{color:var(--gold)}}
@media print{{
  body{{background:#fff;color:#222}}
  .hero{{background:#fff;border-color:#ccc}}
  .omega,.brand,.doc-title{{color:#222}}
  h1,h2{{color:#222;border-color:#ccc}}
  pre{{background:#f5f5f5;border-color:#ddd}}
  th{{background:#eee;color:#222}}
  td{{border-color:#ddd;color:#222}}
}}
</style>
</head>
<body>
<div class="hero">
  <div class="omega">{_escape(brand.logo_text)}</div>
  <div class="brand">VERITAS DOCS</div>
  <div class="doc-title">{_escape(doc.title)}</div>
  {"<div class='doc-sub'>" + _escape(doc.subtitle) + "</div>" if doc.subtitle else ""}
  <div class="doc-date">Generated: {gen_date}</div>
  {"<div class='conf-badge'>" + _escape(conf_label) + "</div>" if conf_label else ""}
</div>
<div class="content">
{body_html}
</div>
<div class="motto">{_escape(brand.logo_text)} {_escape(brand.motto)}</div>
<div class="footer"><span>{_escape(brand.logo_text)}</span> &nbsp; VERITAS DOCS &nbsp;·&nbsp; {_escape(brand.footer_text)}</div>
</body>
</html>'''

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
