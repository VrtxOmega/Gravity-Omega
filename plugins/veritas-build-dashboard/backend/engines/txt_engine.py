"""
VERITAS Docs — Plain Text Engine
==================================
Renders a VeritasDocument to clean UTF-8 plain text.
Features: 80-char word wrap, ASCII box-drawn section separators, fixed-width tables.
"""

import os
import re
import textwrap
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import BrandPreset, VeritasDocument


def _wrap(text: str, width: int = 78) -> str:
    """Word-wrap text to specified width."""
    return '\n'.join(textwrap.wrap(text, width=width))


def _ascii_table(rows: list) -> str:
    """Render a table as fixed-width ASCII."""
    if not rows:
        return ''
    n_cols = max(len(r) for r in rows)
    # Normalize rows to same column count
    norm = [r + [''] * (n_cols - len(r)) for r in rows]
    # Calculate column widths
    widths = [max(len(str(norm[ri][ci])) for ri in range(len(norm))) for ci in range(n_cols)]
    widths = [max(w, 3) for w in widths]

    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    lines = [sep]
    for ri, row in enumerate(norm):
        cells = '|'.join(f' {str(row[ci]).ljust(widths[ci])} ' for ci in range(n_cols))
        lines.append(f'|{cells}|')
        if ri == 0:
            lines.append(sep.replace('-', '='))
    lines.append(sep)
    return '\n'.join(lines)


def render(doc: VeritasDocument, brand: BrandPreset, output_path: Path) -> Path:
    """Render a VeritasDocument to plain text."""
    out = []
    gen_date = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Header
    out.append('=' * 72)
    out.append(f'  {brand.logo_text} VERITAS DOCS')
    out.append(f'  {doc.title}')
    if doc.subtitle:
        out.append(f'  {doc.subtitle}')
    out.append(f'  Generated: {gen_date}')
    conf = brand.confidentiality_label
    if conf:
        out.append(f'  Classification: {conf}')
    out.append('=' * 72)
    out.append('')

    # Parse and render markdown to plain text
    lines = doc.content.split('\n')
    in_code = False
    table_buf = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Code blocks
        if stripped.startswith('```'):
            if in_code:
                in_code = False
                out.append('  ' + '-' * 40)
            else:
                if table_buf:
                    out.append(_ascii_table(table_buf))
                    table_buf = []
                out.append('  ' + '-' * 40)
                in_code = True
            i += 1
            continue
        if in_code:
            out.append(f'  | {line}')
            i += 1
            continue

        if not stripped:
            if table_buf:
                out.append(_ascii_table(table_buf))
                out.append('')
                table_buf = []
            out.append('')
            i += 1
            continue

        # Table rows
        if '|' in stripped and stripped.startswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                i += 1
                continue
            table_buf.append(cells)
            i += 1
            continue
        elif table_buf:
            out.append(_ascii_table(table_buf))
            out.append('')
            table_buf = []

        # Headings
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title = stripped[2:].strip()
            out.append('')
            out.append('=' * 72)
            out.append(f'  {title.upper()}')
            out.append('=' * 72)
            out.append('')
            i += 1
            continue
        if stripped.startswith('## '):
            title = stripped[3:].strip()
            out.append('')
            out.append('-' * 72)
            out.append(f'  {title.upper()}')
            out.append('-' * 72)
            out.append('')
            i += 1
            continue
        if stripped.startswith('### '):
            title = stripped[4:].strip()
            out.append('')
            out.append(f'  [{title}]')
            out.append('')
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^---+$', stripped):
            out.append('')
            out.append('~' * 72)
            out.append('')
            i += 1
            continue

        # Blockquote
        if stripped.startswith('>'):
            text = stripped[1:].strip()
            out.append(f'  >> {_wrap(text, 70)}')
            i += 1
            continue

        # Bullets
        if stripped.startswith('- ') or stripped.startswith('* '):
            text = stripped[2:].strip()
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
            wrapped = textwrap.fill(text, width=72, initial_indent='  * ', subsequent_indent='    ')
            out.append(wrapped)
            i += 1
            continue

        # Body text
        text = stripped
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        out.append(_wrap(text, 78))
        i += 1

    # Flush
    if table_buf:
        out.append(_ascii_table(table_buf))

    # Footer
    out.append('')
    out.append('=' * 72)
    out.append(f'  {brand.motto}')
    out.append(f'  {brand.footer_text}')
    out.append('=' * 72)

    output_text = '\n'.join(out)

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    return output_path
