"""
VERITAS Docs — Markdown Engine
================================
Renders a VeritasDocument to clean GitHub-Flavored Markdown.
Strips all branding — pure content output.
"""

import os
import re
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import BrandPreset, VeritasDocument


def render(doc: VeritasDocument, brand: BrandPreset, output_path: Path) -> Path:
    """Render a VeritasDocument to clean GFM Markdown."""
    lines = []
    gen_date = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Frontmatter-style header
    lines.append(f"# {doc.title}")
    if doc.subtitle:
        lines.append(f"### {doc.subtitle}")
    lines.append("")
    lines.append(f"> Generated: {gen_date}  ")
    lines.append(f"> Source: {doc.source_name}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # The content is already markdown — pass through with cleanup
    content = doc.content.strip()

    # Normalize line endings
    content = content.replace('\r\n', '\n')

    # Ensure consistent heading spacing
    content = re.sub(r'\n(#{1,4} )', r'\n\n\1', content)

    # Remove duplicate blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    lines.append(content)

    # Footer
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*{brand.footer_text}*")

    output_text = '\n'.join(lines)

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    return output_path
