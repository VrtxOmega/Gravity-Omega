"""
VERITAS Docs — Slide Engine
==============================
Renders a VeritasDocument to an HTML slide deck.
Arrow-key navigation, VERITAS dark theme, fade transitions.
Each ## Section becomes a slide. ### becomes a sub-point.
"""

import os
import re
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import BrandPreset, VeritasDocument


def _escape(text: str) -> str:
    return (text.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))


def _inline(text: str) -> str:
    text = _escape(text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def _parse_slides(md_text: str, title: str) -> list:
    """Parse markdown into slides. Each ## creates a new slide."""
    slides = []
    current = {'title': title, 'content': [], 'is_title_slide': True}

    for line in md_text.split('\n'):
        stripped = line.strip()

        if stripped.startswith('## '):
            # Save current slide
            if current['content'] or current['is_title_slide']:
                slides.append(current)
            current = {
                'title': stripped[3:].strip(),
                'content': [],
                'is_title_slide': False,
            }
            continue

        if stripped.startswith('# ') and not stripped.startswith('## '):
            # Title slide header — skip if we already have one
            continue

        if stripped.startswith('### '):
            current['content'].append(('h3', stripped[4:].strip()))
        elif stripped.startswith('- ') or stripped.startswith('* '):
            current['content'].append(('bullet', stripped[2:].strip()))
        elif stripped.startswith('>'):
            current['content'].append(('quote', stripped[1:].strip()))
        elif re.match(r'^---+$', stripped):
            # Force new slide
            if current['content'] or current['is_title_slide']:
                slides.append(current)
            current = {'title': '', 'content': [], 'is_title_slide': False}
        elif stripped.startswith('```'):
            current['content'].append(('code_marker', ''))
        elif stripped:
            current['content'].append(('text', stripped))

    if current['content'] or current['is_title_slide']:
        slides.append(current)

    return slides


def _render_slide(slide: dict, index: int, total: int, brand: BrandPreset) -> str:
    """Render a single slide to HTML."""
    content_parts = []

    if slide['is_title_slide']:
        # Title slide
        content_parts.append(f'<div class="slide-omega">{_escape(brand.logo_text)}</div>')
        content_parts.append(f'<div class="slide-brand">VERITAS DOCS</div>')
        content_parts.append(f'<div class="slide-title">{_escape(slide["title"])}</div>')
        content_parts.append(f'<div class="slide-date">{datetime.now().strftime("%B %d, %Y")}</div>')
    else:
        content_parts.append(f'<h2 class="slide-heading">{_inline(slide["title"])}</h2>')
        in_code = False
        code_buf = []
        for typ, text in slide['content']:
            if typ == 'code_marker':
                if in_code:
                    content_parts.append(f'<pre><code>{"".join(code_buf)}</code></pre>')
                    code_buf = []
                    in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_buf.append(_escape(text) + '\n')
                continue
            if typ == 'h3':
                content_parts.append(f'<h3>{_inline(text)}</h3>')
            elif typ == 'bullet':
                content_parts.append(f'<div class="slide-bullet">▸ {_inline(text)}</div>')
            elif typ == 'quote':
                content_parts.append(f'<div class="slide-quote">{_inline(text)}</div>')
            elif typ == 'text':
                content_parts.append(f'<p>{_inline(text)}</p>')
        if code_buf:
            content_parts.append(f'<pre><code>{"".join(code_buf)}</code></pre>')

    body = '\n    '.join(content_parts)
    return f'''<div class="slide" data-index="{index}">
    <div class="slide-content">
    {body}
    </div>
    <div class="slide-footer">
      <span class="slide-counter">{index + 1} / {total}</span>
      <span class="slide-logo">{_escape(brand.logo_text)} VERITAS DOCS</span>
    </div>
  </div>'''


def render(doc: VeritasDocument, brand: BrandPreset, output_path: Path) -> Path:
    """Render a VeritasDocument to an HTML slide deck."""
    slides = _parse_slides(doc.content, doc.title)
    total = len(slides)

    slides_html = '\n'.join(
        _render_slide(s, i, total, brand) for i, s in enumerate(slides)
    )

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape(doc.title)} — VERITAS Slides</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden;background:{brand.obsidian};color:{brand.warm_white}}}
.slide{{position:fixed;top:0;left:0;width:100%;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:60px 80px;opacity:0;pointer-events:none;transition:opacity 0.4s ease}}
.slide.active{{opacity:1;pointer-events:all}}
.slide-content{{max-width:900px;width:100%;text-align:left}}
.slide-omega{{font-family:'Orbitron',monospace;font-size:96px;font-weight:900;color:{brand.gold};text-shadow:0 0 12px rgba(240,192,64,0.7),0 0 50px rgba(201,168,76,.4);line-height:1;margin-bottom:16px;text-align:center}}
.slide-brand{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:20px;letter-spacing:10px;color:{brand.gold};text-transform:uppercase;text-align:center;margin-bottom:8px}}
.slide-title{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:36px;color:{brand.gold};text-align:center;margin-top:24px}}
.slide-date{{font-family:'Share Tech Mono',monospace;font-size:13px;color:#999;text-align:center;margin-top:12px}}
.slide-heading{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:28px;color:{brand.gold};letter-spacing:2px;margin-bottom:24px;border-bottom:2px solid {brand.gold};padding-bottom:10px}}
h3{{font-family:'Rajdhani',sans-serif;font-weight:600;font-size:18px;color:#CCC;margin:20px 0 10px}}
p{{font-family:'Share Tech Mono',monospace;font-size:16px;line-height:1.8;margin:10px 0;color:{brand.warm_white}}}
.slide-bullet{{font-family:'Share Tech Mono',monospace;font-size:16px;line-height:2;color:{brand.warm_white};padding-left:8px}}
.slide-bullet strong{{color:{brand.gold}}}
.slide-quote{{border-left:3px solid {brand.gold};padding:10px 20px;margin:14px 0;font-style:italic;color:{brand.gold_dim};font-size:15px}}
code{{font-family:'Share Tech Mono',monospace;background:#111;padding:2px 6px;border:1px solid #222;color:{brand.gold_dim}}}
pre{{background:#0a0a0a;border:1px solid #2a1f08;padding:16px;margin:12px 0;border-radius:0;overflow-x:auto}}
pre code{{background:none;border:none;padding:0;color:#888;font-size:13px}}
strong{{color:{brand.gold}}}
em{{color:#999}}
a{{color:{brand.gold};text-decoration:none}}
.slide-footer{{position:absolute;bottom:20px;left:0;right:0;display:flex;justify-content:space-between;padding:0 40px}}
.slide-counter{{font-family:'Rajdhani',sans-serif;font-size:12px;letter-spacing:3px;color:{brand.gold_dim}}}
.slide-logo{{font-family:'Orbitron',monospace;font-size:10px;letter-spacing:2px;color:{brand.gold_dim}}}
@media print{{
  .slide{{position:relative !important;opacity:1 !important;pointer-events:all !important;page-break-after:always;height:auto;min-height:100vh}}
  .slide-footer{{position:relative;margin-top:40px}}
}}
</style>
</head>
<body>
{slides_html}
<script>
let current = 0;
const slides = document.querySelectorAll('.slide');
function showSlide(n) {{
  slides.forEach(s => s.classList.remove('active'));
  current = Math.max(0, Math.min(n, slides.length - 1));
  slides[current].classList.add('active');
}}
showSlide(0);
document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === ' ') showSlide(current + 1);
  if (e.key === 'ArrowLeft') showSlide(current - 1);
  if (e.key === 'Home') showSlide(0);
  if (e.key === 'End') showSlide(slides.length - 1);
}});
// Touch/swipe support
let touchX = 0;
document.addEventListener('touchstart', e => {{ touchX = e.touches[0].clientX; }});
document.addEventListener('touchend', e => {{
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 50) showSlide(current + (dx < 0 ? 1 : -1));
}});
</script>
</body>
</html>'''

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
