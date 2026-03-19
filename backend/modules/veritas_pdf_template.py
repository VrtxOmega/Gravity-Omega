from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── BRAND COLORS ────────────────────────────────────────────────────────────
GOLD        = HexColor('#C9A84C')
DARK        = HexColor('#0D0D0D')
MID_GRAY    = HexColor('#333333')
LIGHT_GRAY  = HexColor('#666666')
ROW_A       = HexColor('#F9F9F7')
ROW_B       = HexColor('#EFEFEB')
RULE        = HexColor('#CCCCCC')
ACCENT      = HexColor('#AAAAAA')

# ── STYLES ───────────────────────────────────────────────────────────────────
def build_styles():
    return {
        # Cover / hero text
        'Cover_Title': ParagraphStyle('Cover_Title',
            fontName='Helvetica-Bold', fontSize=28,
            textColor=GOLD, spaceAfter=8, leading=34, alignment=TA_LEFT),

        'Cover_Sub': ParagraphStyle('Cover_Sub',
            fontName='Helvetica', fontSize=13,
            textColor=HexColor('#AAAAAA'), spaceAfter=6, leading=18),

        'Cover_Meta': ParagraphStyle('Cover_Meta',
            fontName='Helvetica', fontSize=10,
            textColor=HexColor('#888888'), spaceAfter=4, leading=14),

        'Cover_Tagline': ParagraphStyle('Cover_Tagline',
            fontName='Helvetica-Oblique', fontSize=11,
            textColor=GOLD, spaceAfter=4, leading=16),

        # Section headers
        'Section_Header': ParagraphStyle('Section_Header',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=GOLD, spaceBefore=18, spaceAfter=6, leading=16),

        'Subsection': ParagraphStyle('Subsection',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=HexColor('#CCCCCC'), spaceBefore=10, spaceAfter=4, leading=14),

        # Body text
        'Body': ParagraphStyle('Body',
            fontName='Helvetica', fontSize=10,
            textColor=MID_GRAY, spaceAfter=6, leading=15, alignment=TA_JUSTIFY),

        'Bullet': ParagraphStyle('Bullet',
            fontName='Helvetica', fontSize=10,
            textColor=MID_GRAY, spaceAfter=4, leading=14,
            leftIndent=16, firstLineIndent=-10),

        'Mono': ParagraphStyle('Mono',
            fontName='Courier', fontSize=9,
            textColor=HexColor('#444444'), spaceAfter=4, leading=13),

        'Footer': ParagraphStyle('Footer',
            fontName='Helvetica', fontSize=8,
            textColor=HexColor('#999999'), leading=11, alignment=TA_CENTER),
    }

# ── PAGE FOOTER ──────────────────────────────────────────────────────────────
def add_page_number(canvas, doc):
    """Adds gold rule + page number to every page."""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor('#999999'))
    # Change the footer text below
    canvas.drawCentredString(4.25*inch, 0.5*inch,
        f"VERITAS &#937; — Document Title — Page {doc.page}")
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(inch, 0.7*inch, 7.5*inch, 0.7*inch)
    canvas.restoreState()

# ── TABLE HELPER ─────────────────────────────────────────────────────────────
def make_table(data, col_widths):
    """
    Builds a styled gold-header table.
    data: list of lists. First row = headers.
    col_widths: list of widths in inches, e.g. [1.5*inch, 3.0*inch, 1.5*inch]
    """
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  GOLD),
        ('TEXTCOLOR',     (0,0), (-1,0),  DARK),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('TEXTCOLOR',     (0,1), (-1,-1), HexColor('#222222')),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [ROW_A, ROW_B]),
        ('GRID',          (0,0), (-1,-1), 0.5, RULE),
        ('ALIGN',         (0,0), (-1,-1), 'LEFT'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
    ]))
    return t

# ── DOCUMENT BUILDER ─────────────────────────────────────────────────────────
def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=inch, rightMargin=inch,
        topMargin=inch,  bottomMargin=0.9*inch
    )

    S = build_styles()
    story = []

    # ── COVER PAGE ────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("VERITAS &#937;", S['Cover_Sub']))
    story.append(Paragraph("Document Title Here", S['Cover_Title']))
    story.append(Paragraph("Subtitle or tagline here", S['Cover_Sub']))
    story.append(Spacer(1, 0.15*inch))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=12))
    story.append(Spacer(1, 0.1*inch))

    # Cover metadata block
    story.append(Paragraph("Label: Value", S['Cover_Meta']))
    story.append(Paragraph("Label: Value", S['Cover_Meta']))
    story.append(Paragraph("Label: Value", S['Cover_Meta']))
    story.append(Spacer(1, 0.4*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=12))
    story.append(Spacer(1, 0.2*inch))

    # Closing tagline on cover
    story.append(Paragraph(
        "VERITAS &#937; does not determine what is true.<br/>"
        "It determines what reality refuses to let go of.",
        S['Cover_Tagline']))
    story.append(PageBreak())

    # ── SECTION 1 ─────────────────────────────────────────────────────────
    story.append(Paragraph("Section Title", S['Section_Header']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=8))
    story.append(Paragraph(
        "Body text goes here. This style is justified and readable at 10pt. "
        "Replace this with your actual content.",
        S['Body']))

    # Subsection
    story.append(Paragraph("Subsection Title", S['Subsection']))
    story.append(Paragraph("Subsection body text here.", S['Body']))

    # Bullet list
    for item in ["First bullet point", "Second bullet point", "Third bullet point"]:
        story.append(Paragraph(f"&#8226; {item}", S['Bullet']))

    # ── TABLE EXAMPLE ─────────────────────────────────────────────────────
    story.append(Paragraph("Table Example", S['Section_Header']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=8))

    table_data = [
        ['Column 1', 'Column 2', 'Column 3'],
        ['Row 1A',   'Row 1B',   'Row 1C'],
        ['Row 2A',   'Row 2B',   'Row 2C'],
        ['Row 3A',   'Row 3B',   'Row 3C'],
    ]
    story.append(make_table(table_data, [2.0*inch, 2.5*inch, 1.5*inch]))
    story.append(Spacer(1, 0.1*inch))

    # ── PAGE BREAK + NEW SECTION ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Second Page Section", S['Section_Header']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=8))
    story.append(Paragraph("Content on second page.", S['Body']))

    # ── CLOSING ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=12))
    story.append(Paragraph("Closing statement or call to action.", S['Body']))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Not believers. Verifiers.", S['Cover_Tagline']))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "RJ Lopez | RJ@AegisAudits.com | @RJLopezAI | aegisaudits.com",
        S['Cover_Meta']))
    story.append(Paragraph(
        "ETH: 0x36c54AF7aCe58E04eebc1cc593547d02803e5a7d",
        S['Cover_Meta']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "VERITAS &#937; does not determine what is true. "
        "It determines what reality refuses to let go of.",
        S['Cover_Tagline']))

    # ── BUILD ─────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF generated: {output_path}")

if __name__ == "__main__":
    build_pdf("/mnt/user-data/outputs/veritas_template.pdf")
