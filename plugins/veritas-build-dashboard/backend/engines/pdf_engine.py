"""
VERITAS Docs — PDF Engine
==========================
Renders a VeritasDocument to a branded VERITAS Ω PDF.
Ported from veritas_pdf.py (577 lines) and enhanced with
QR provenance, confidentiality stamps, and watermark support.
"""

import os
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Preformatted
)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import BrandPreset, VeritasDocument


# ── INLINE FORMATTING ────────────────────────────────────────

def format_inline(text):
    """Convert markdown inline formatting to ReportLab XML tags."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Stash inline code spans
    code_tokens = []
    def _stash_code(m):
        token = f'\x00CODE{len(code_tokens)}\x00'
        code_tokens.append(f'<font face="Courier" size="9">{m.group(1)}</font>')
        return token
    text = re.sub(r'`(.+?)`', _stash_code, text)

    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    # Links: [text](url) → just show text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    # Restore code tokens
    for i, replacement in enumerate(code_tokens):
        text = text.replace(f'\x00CODE{i}\x00', replacement)

    return text


def build_styles(brand: BrandPreset):
    """Build ReportLab paragraph styles from brand preset."""
    GOLD = HexColor(brand.gold)
    MID_GRAY = HexColor(brand.mid_gray)
    LT_GRAY = HexColor('#666666')

    return {
        'Cover_Title': ParagraphStyle('Cover_Title',
            fontName='Helvetica-Bold', fontSize=28,
            textColor=GOLD, spaceAfter=8, leading=34, alignment=TA_LEFT),
        'Cover_Sub': ParagraphStyle('Cover_Sub',
            fontName='Helvetica', fontSize=13,
            textColor=HexColor('#AAAAAA'), spaceAfter=6, leading=18),
        'Cover_Meta': ParagraphStyle('Cover_Meta',
            fontName='Helvetica', fontSize=10,
            textColor=HexColor('#888888'), spaceAfter=4, leading=14),
        'Cover_Date': ParagraphStyle('Cover_Date',
            fontName='Helvetica', fontSize=10,
            textColor=HexColor('#999999'), spaceAfter=4, leading=14),
        'Cover_Tagline': ParagraphStyle('Cover_Tagline',
            fontName='Helvetica-Oblique', fontSize=11,
            textColor=GOLD, spaceAfter=4, leading=16),
        'Section_Header': ParagraphStyle('Section_Header',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=GOLD, spaceBefore=18, spaceAfter=6, leading=16),
        'Subsection': ParagraphStyle('Subsection',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=HexColor('#CCCCCC'), spaceBefore=10, spaceAfter=4, leading=14),
        'Body': ParagraphStyle('Body',
            fontName='Helvetica', fontSize=10,
            textColor=MID_GRAY, spaceAfter=6, leading=15, alignment=TA_JUSTIFY),
        'Body_Bold': ParagraphStyle('Body_Bold',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=MID_GRAY, spaceAfter=6, leading=15, alignment=TA_JUSTIFY),
        'Body_Italic': ParagraphStyle('Body_Italic',
            fontName='Helvetica-Oblique', fontSize=10,
            textColor=LT_GRAY, spaceAfter=6, leading=15, alignment=TA_JUSTIFY),
        'Bullet': ParagraphStyle('Bullet',
            fontName='Helvetica', fontSize=10,
            textColor=MID_GRAY, spaceAfter=4, leading=14,
            leftIndent=16, firstLineIndent=-10),
        'Mono': ParagraphStyle('Mono',
            fontName='Courier', fontSize=8.5,
            textColor=HexColor('#444444'), spaceAfter=4, leading=12,
            leftIndent=12),
        'TOC_H1': ParagraphStyle('TOC_H1',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=GOLD, spaceBefore=6, spaceAfter=2, leading=14,
            leftIndent=0),
        'TOC_H2': ParagraphStyle('TOC_H2',
            fontName='Helvetica', fontSize=10,
            textColor=MID_GRAY, spaceBefore=2, spaceAfter=2, leading=13,
            leftIndent=20),
        'Watermark': ParagraphStyle('Watermark',
            fontName='Helvetica-Bold', fontSize=48,
            textColor=HexColor('#CCCCCC'), alignment=TA_CENTER),
    }


def make_table(rows, brand: BrandPreset):
    """Build a branded table from a list of string lists."""
    GOLD = HexColor(brand.gold)
    DARK = HexColor('#0D0D0D')
    ROW_A = HexColor('#F9F9F7')
    ROW_B = HexColor('#EFEFEB')
    RULE = HexColor('#CCCCCC')

    avail_width = 6.5 * inch

    header_style = ParagraphStyle('TableHeader',
        fontName='Helvetica-Bold', fontSize=9, textColor=DARK, leading=12, wordWrap='CJK')
    cell_style = ParagraphStyle('TableCell',
        fontName='Helvetica', fontSize=9, textColor=HexColor('#222222'), leading=12, wordWrap='CJK')

    wrapped = []
    for ri, row in enumerate(rows):
        style = header_style if ri == 0 else cell_style
        wrapped.append([Paragraph(format_inline(str(c)), style) for c in row])

    if rows:
        n_cols = max(len(r) for r in rows)
        max_lens = [0] * n_cols
        for row in rows:
            for ci, cell in enumerate(row):
                if ci < n_cols:
                    max_lens[ci] = max(max_lens[ci], len(str(cell)))
        total_len = max(sum(max_lens), 1)
        min_col = 0.8 * inch
        col_widths = [max(min_col, (ml / total_len) * avail_width) for ml in max_lens]
        scale = avail_width / sum(col_widths)
        col_widths = [w * scale for w in col_widths]
    else:
        col_widths = None

    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GOLD),
        ('TEXTCOLOR', (0, 0), (-1, 0), DARK),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('TEXTCOLOR', (0, 1), (-1, -1), HexColor('#222222')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [ROW_A, ROW_B]),
        ('GRID', (0, 0), (-1, -1), 0.5, RULE),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def parse_markdown(md_text, title_override=None, subtitle_override=None):
    """Parse markdown into (element_type, content) tuples."""
    lines = md_text.split('\n')
    elements = []
    first_h1_seen = False
    in_code_block = False
    code_buffer = []
    table_buffer = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith('```'):
            if in_code_block:
                elements.append(('code', '\n'.join(code_buffer)))
                code_buffer = []
                in_code_block = False
            else:
                if table_buffer:
                    elements.append(('table', table_buffer))
                    table_buffer = []
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue

        stripped = line.strip()

        if not stripped:
            if table_buffer:
                elements.append(('table', table_buffer))
                table_buffer = []
            i += 1
            continue

        if '|' in stripped and stripped.startswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                i += 1
                continue
            table_buffer.append(cells)
            i += 1
            continue
        else:
            if table_buffer:
                elements.append(('table', table_buffer))
                table_buffer = []

        if re.match(r'^---+$', stripped):
            elements.append(('pagebreak', None))
            i += 1
            continue

        if stripped.startswith('# ') and not stripped.startswith('## '):
            title_text = stripped[2:].strip()
            if not first_h1_seen:
                elements.append(('cover_title', title_override or title_text))
                first_h1_seen = True
            else:
                elements.append(('section', title_text))
            i += 1
            if i < len(lines) and lines[i].strip().startswith('### '):
                sub_text = lines[i].strip()[4:].strip()
                elements.append(('cover_sub', subtitle_override or sub_text))
                i += 1
            continue

        if stripped.startswith('## '):
            elements.append(('section', stripped[3:].strip()))
            i += 1
            continue

        if stripped.startswith('### '):
            elements.append(('subsection', stripped[4:].strip()))
            i += 1
            continue

        if stripped.startswith('>'):
            elements.append(('blockquote', stripped[1:].strip()))
            i += 1
            continue

        if stripped.startswith('- ') or stripped.startswith('* '):
            elements.append(('bullet', stripped[2:].strip()))
            i += 1
            continue

        if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
            elements.append(('bold', stripped[2:-2]))
            i += 1
            continue

        if stripped.startswith('*') and stripped.endswith('*') and not stripped.startswith('**'):
            elements.append(('italic', stripped[1:-1]))
            i += 1
            continue

        elements.append(('body', stripped))
        i += 1

    if table_buffer:
        elements.append(('table', table_buffer))
    if code_buffer:
        elements.append(('code', '\n'.join(code_buffer)))

    return elements


def _add_page_decor(canvas, doc, brand: BrandPreset):
    """Page footer with branding + confidentiality."""
    GOLD = HexColor(brand.gold)
    canvas.saveState()

    # Footer line + page number
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor('#999999'))
    canvas.drawCentredString(4.25 * inch, 0.5 * inch,
                             f"VERITAS \u03a9 \u2014 Page {doc.page}")
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(inch, 0.7 * inch, 7.5 * inch, 0.7 * inch)

    # Confidentiality badge (top right)
    conf_label = brand.confidentiality_label
    if conf_label:
        canvas.setFont('Helvetica-Bold', 7)
        canvas.setFillColor(HexColor(brand.confidentiality_color))
        canvas.drawRightString(7.5 * inch, 10.3 * inch, conf_label)

    # Watermark (diagonal across center)
    wm = brand.watermark or (conf_label if brand.confidentiality in ("confidential", "restricted") else None)
    if wm:
        canvas.saveState()
        canvas.translate(4.25 * inch, 5.5 * inch)
        canvas.rotate(45)
        canvas.setFont('Helvetica-Bold', 60)
        canvas.setFillColor(HexColor('#CCCCCC'))
        canvas.setFillAlpha(brand.watermark_opacity)
        canvas.drawCentredString(0, 0, wm)
        canvas.restoreState()

    canvas.restoreState()


def build_story(elements, styles, brand: BrandPreset):
    """Convert parsed elements into ReportLab flowables."""
    S = styles
    GOLD = HexColor(brand.gold)
    RULE = HexColor('#CCCCCC')
    story = []
    after_cover_title = False
    cover_done = False
    toc_entries = []
    section_idx = 0
    gen_date = datetime.now().strftime('%B %d, %Y \u2014 %H:%M')

    # Motto text for cover page
    motto_text = brand.motto.replace('. ', '.<br/>')

    for etype, content in elements:

        if etype == 'cover_title':
            story.append(Spacer(1, 0.8 * inch))
            story.append(Paragraph("VERITAS &#937;", S['Cover_Sub']))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(format_inline(content), S['Cover_Title']))
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph(f"Generated: {gen_date}", S['Cover_Date']))
            after_cover_title = True

        elif etype == 'cover_sub':
            story.append(Paragraph(format_inline(content), S['Cover_Sub']))
            story.append(Spacer(1, 0.15 * inch))
            story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=12))
            after_cover_title = False

        elif etype == 'section':
            if after_cover_title and not cover_done:
                story.append(Spacer(1, 0.3 * inch))
                story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=12))
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph(motto_text, S['Cover_Tagline']))
                cover_done = True
                after_cover_title = False
                story.append(PageBreak())
            section_idx += 1
            anchor = f'section_{section_idx}'
            toc_entries.append((0, content, anchor))
            story.append(Paragraph(
                f'<a name="{anchor}"/>{format_inline(content)}',
                S['Section_Header']))
            story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=8))

        elif etype == 'subsection':
            section_idx += 1
            anchor = f'section_{section_idx}'
            toc_entries.append((1, content, anchor))
            story.append(Paragraph(
                f'<a name="{anchor}"/>{format_inline(content)}',
                S['Subsection']))

        elif etype == 'body':
            story.append(Paragraph(format_inline(content), S['Body']))
        elif etype == 'bold':
            story.append(Paragraph(format_inline(content), S['Body_Bold']))
        elif etype == 'italic':
            story.append(Paragraph(format_inline(content), S['Body_Italic']))
        elif etype == 'bullet':
            story.append(Paragraph(f"&#8226; {format_inline(content)}", S['Bullet']))
        elif etype == 'blockquote':
            story.append(Paragraph(format_inline(content), S['Cover_Tagline']))
        elif etype == 'code':
            for code_line in content.split('\n'):
                safe = code_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(safe, S['Mono']))
        elif etype == 'table':
            story.append(Spacer(1, 0.05 * inch))
            story.append(make_table(content, brand))
            story.append(Spacer(1, 0.1 * inch))
        elif etype == 'pagebreak':
            if not cover_done and after_cover_title:
                story.append(Spacer(1, 0.3 * inch))
                story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=12))
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph(motto_text, S['Cover_Tagline']))
                cover_done = True
                after_cover_title = False
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 0.08 * inch))
                story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=8))
                story.append(Spacer(1, 0.05 * inch))

    # Closing footer
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=12))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(motto_text, S['Cover_Tagline']))

    # Insert TOC after cover page
    if toc_entries:
        toc_story = []
        toc_story.append(Paragraph("Table of Contents", S['Section_Header']))
        toc_story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=8))
        for level, title, anchor in toc_entries:
            style = S['TOC_H1'] if level == 0 else S['TOC_H2']
            prefix = '' if level == 0 else '    '
            toc_story.append(Paragraph(
                f'{prefix}<a href="#{anchor}" color="#C9A84C">{format_inline(title)}</a>',
                style))
        toc_story.append(PageBreak())
        insert_idx = 0
        for idx, item in enumerate(story):
            if isinstance(item, PageBreak):
                insert_idx = idx + 1
                break
        for i, item in enumerate(toc_story):
            story.insert(insert_idx + i, item)

    return story


def render(doc: VeritasDocument, brand: BrandPreset, output_path: Path, trace_id: str = None) -> Path:
    """Render a VeritasDocument to a branded PDF."""
    if trace_id is None:
        try:
            trace_id = output_path.stem.split('_')[-1]
        except:
            trace_id = "VD-UNTRACKED"

    # Normalize unicode for PDF standard fonts
    md_text = doc.content
    replacements = {
        '\u2013': '-', '\u2014': '--', '\u2011': '-',
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u00a0': ' ', '\u2026': '...', '\uFEFF': ''
    }
    for k, v in replacements.items():
        md_text = md_text.replace(k, v)

    # Synthesize H1 if none exists
    if not re.search(r'^# ', md_text, flags=re.MULTILINE):
        lines = [l for l in md_text.split('\n') if l.strip()]
        if lines:
            title = lines[0].strip().replace('**', '').replace('__', '').lstrip('#').strip()
            md_text = f"# {title}\n\n" + "\n".join(lines[1:])

    elements = parse_markdown(md_text, title_override=doc.title, subtitle_override=doc.subtitle)
    styles = build_styles(brand)
    story = build_story(elements, styles, brand)

    # Add QR Code Page
    import qrcode
    import tempfile
    from reportlab.platypus import Image
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(f"veritasdocs://receipt/{trace_id}")
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color=brand.gold, back_color="transparent")
    
    # Store temporary image to stick into ReportLab
    fd, temp_path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    qr_img.save(temp_path)
    
    story.append(PageBreak())
    story.append(Spacer(1, 3.5 * inch))
    story.append(Paragraph("DOCUMENT PROVENANCE", styles['Cover_Title']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor(brand.gold), spaceAfter=24))
    story.append(Image(temp_path, width=2.5*inch, height=2.5*inch, hAlign='LEFT'))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"<b>Trace ID:</b> {trace_id}", styles['Body']))
    story.append(Paragraph(f"<b>Classification:</b> {brand.confidentiality.upper()}", styles['Body']))
    story.append(Paragraph("This cryptographically sealed hash points to the original unaltered receipt.", styles['Cover_Meta']))


    os.makedirs(output_path.parent, exist_ok=True)

    pdf_doc = SimpleDocTemplate(
        str(output_path), pagesize=letter,
        leftMargin=inch, rightMargin=inch,
        topMargin=inch, bottomMargin=0.9 * inch
    )

    def page_handler(canvas, doc_obj):
        _add_page_decor(canvas, doc_obj, brand)

    pdf_doc.build(story, onFirstPage=page_handler, onLaterPages=page_handler)
    
    # Clean up temp file safely
    try:
        os.remove(temp_path)
    except Exception as e:
        pass
        
    return output_path
