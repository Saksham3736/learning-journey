import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and display total page count.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Master C++ & Data Structures & Algorithms (DSA) Syllabus")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
            
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_text)
        self.drawString(54, 36, "Learning Journey Repository | Production-Grade Knowledge Base")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)
        
        self.restoreState()

def clean_md_inline(text):
    """Convert basic inline markdown (bold, italic, code, math) to reportlab HTML tags safely."""
    # First escape HTML special characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 1. Inline code `code` (restore escaped < and > inside code tags if needed)
    def repl_code(match):
        code_content = match.group(1)
        return f'<font face="Courier" color="#0f172a" size="9"><b>{code_content}</b></font>'
    text = re.sub(r'`(.*?)`', repl_code, text)

    # 2. Math expressions $O(N)$ -> <i>O(N)</i>
    text = re.sub(r'\$(.*?)\$', r'<i>\1</i>', text)

    # 3. Bold + Italic ***text***
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)

    # 4. Bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # 5. Italic *text*
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)

    # 6. Italic _text_ (using word boundaries)
    text = re.sub(r'\b_([a-zA-Z0-9\s]+)_\b', r'<i>\1</i>', text)

    # 7. Hyperlinks [text](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<font color="#1d4ed8"><u>\1</u></font>', text)

    return text

def parse_markdown_to_pdf(md_path, pdf_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1e3a8a")     # Deep Navy
    SECONDARY = colors.HexColor("#0284c7")   # Cerulean
    DARK_NEUTRAL = colors.HexColor("#0f172a")# Slate Dark
    MUTED = colors.HexColor("#475569")       # Slate Muted
    BG_CODE = colors.HexColor("#f8fafc")     # Light Slate Tint
    BORDER_CODE = colors.HexColor("#cbd5e1") # Border Grey

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=10,
        alignment=0
    )

    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=PRIMARY,
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=SECONDARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Header3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=DARK_NEUTRAL,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=DARK_NEUTRAL,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b")
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    story = []
    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\r\n')
        stripped = line.strip()

        # Handle Code Blocks
        if stripped.startswith('```'):
            if in_code_block:
                # End of code block
                code_text = "<br/>".join([
                    line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
                    for line in code_lines
                ])
                p = Paragraph(code_text, code_style)
                t = Table([[p]], colWidths=[7.0 * inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), BG_CODE),
                    ('BOX', (0, 0), (-1, -1), 1, BORDER_CODE),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Tables
        if stripped.startswith('|') and stripped.endswith('|'):
            # Table row
            cells = [clean_md_inline(c.strip()) for c in stripped.split('|')[1:-1]]
            # Check if separator row like | :--- | :--- |
            if all(re.match(r'^:?-+:?$', c) for c in cells):
                i += 1
                continue
            table_rows.append(cells)
            i += 1
            # Check if next line is not table
            if i >= len(lines) or not lines[i].strip().startswith('|'):
                # Render table
                if table_rows:
                    num_cols = max(len(r) for r in table_rows)
                    col_w = (7.0 * inch) / num_cols
                    table_data = []
                    for r_idx, row in enumerate(table_rows):
                        formatted_row = []
                        for cell in row:
                            st = body_style if r_idx > 0 else ParagraphStyle('THead', parent=body_style, fontName='Helvetica-Bold', textColor=PRIMARY)
                            formatted_row.append(Paragraph(cell, st))
                        table_data.append(formatted_row)
                    
                    t = Table(table_data, colWidths=[col_w] * num_cols)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ]))
                    story.append(Spacer(1, 6))
                    story.append(t)
                    story.append(Spacer(1, 8))
                table_rows = []
            continue

        # Ignore empty lines
        if not stripped:
            i += 1
            continue

        # Horizontal Rule
        if stripped in ['---', '***', '___']:
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=10, spaceAfter=10))
            i += 1
            continue

        # Headings
        if stripped.startswith('# '):
            text = clean_md_inline(stripped[2:])
            story.append(Paragraph(text, title_style))
            story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceBefore=4, spaceAfter=12))
            i += 1
            continue

        if stripped.startswith('## '):
            text = clean_md_inline(stripped[3:])
            story.append(Paragraph(text, h1_style))
            i += 1
            continue

        if stripped.startswith('### '):
            text = clean_md_inline(stripped[4:])
            story.append(Paragraph(text, h2_style))
            i += 1
            continue

        if stripped.startswith('#### ') or stripped.startswith('##### '):
            prefix_len = 5 if stripped.startswith('#### ') else 6
            text = clean_md_inline(stripped[prefix_len:])
            story.append(Paragraph(text, h3_style))
            i += 1
            continue

        # Blockquote / Callout
        if stripped.startswith('> '):
            text = clean_md_inline(stripped[2:])
            p = Paragraph(text, callout_style)
            t = Table([[p]], colWidths=[7.0 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LINELEFT', (0, 0), (0, 0), 4, SECONDARY),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Bullet List Items
        if stripped.startswith('* ') or stripped.startswith('- ') or re.match(r'^\d+\.\s', stripped):
            # Check checklist item
            item_text = re.sub(r'^\*\s+|^-\s+|^\d+\.\s+', '', stripped)
            if item_text.startswith('[ ] '):
                bullet_char = "❏ "
                item_text = item_text[4:]
            elif item_text.startswith('[x] ') or item_text.startswith('[X] '):
                bullet_char = "✔ "
                item_text = item_text[4:]
            else:
                bullet_char = "• "

            formatted_text = bullet_char + clean_md_inline(item_text)
            
            # Compute indentation level based on leading spaces
            indent = len(line) - len(line.lstrip())
            custom_bullet_style = ParagraphStyle(
                'SubBullet',
                parent=bullet_style,
                leftIndent=15 + indent * 4
            )
            story.append(Paragraph(formatted_text, custom_bullet_style))
            i += 1
            continue

        # Regular Paragraph
        formatted_text = clean_md_inline(stripped)
        story.append(Paragraph(formatted_text, body_style))
        i += 1

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF successfully generated at: {pdf_path}")

if __name__ == "__main__":
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_file = os.path.join(workspace_root, "DSA", "DSA_Syllabus.md")
    pdf_file = os.path.join(workspace_root, "DSA", "DSA_Syllabus.pdf")
    
    if os.path.exists(md_file):
        parse_markdown_to_pdf(md_file, pdf_file)
    else:
        print(f"❌ Could not find source markdown file at: {md_file}")
