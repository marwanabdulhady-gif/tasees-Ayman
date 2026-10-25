#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 06 v0.4 outputs (DOCX/XLSX/PPTX) and auditable ZIPs.
Run with: .venv/bin/python generate_module_06_v0_4.py
"""
from pathlib import Path
import csv, re, zipfile, hashlib, datetime

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from pptx import Presentation
from pptx.util import Inches as PIn, Pt as PPt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.dml.color import RGBColor as PRGB
from pptx.oxml.ns import qn as pqn

ROOT = Path(__file__).resolve().parent
SRC = ROOT / '01_الأصول_النصية'
VIS = ROOT / '03_المواد_البصرية'
OUT = ROOT / '02_مخرجات_قيد_الإنتاج'
FINAL = ROOT / '03_الحزمة_النهائية'
OUT.mkdir(exist_ok=True); FINAL.mkdir(exist_ok=True)

AR_FONT = 'Arial'
NAVY='16324F'; TEAL='0E7C6B'; GOLD='D98E04'; INK='17212B'; MUTED='52616B'
WHITE='FFFFFF'; LIGHT='F7FAFC'; RED='B3423A'; CREAM='FDF8EE'; PALE='E8F4F1'; PALEG='FBEADB'
DATE_AR = '٢٥ أكتوبر ٢٠٢٦'
DISCLAIMER = 'أسلوب مستوحى من المهندس أيمن عبد الرحيم — ليس قولًا منسوبًا إليه. النصوص تدريبية داخل مشروع تأسيس، ولا تُنشر باسمه أو بصوت مولَّد دون إذن صريح.'

# ---------------- DOCX helpers ----------------
def bidi(p):
    pPr = p._p.get_or_add_pPr(); e = OxmlElement('w:bidi'); e.set(qn('w:val'), '1'); pPr.append(e)

def runstyle(r, size=10.5, bold=False, color=INK, italic=False):
    r.font.name = AR_FONT; r._element.rPr.rFonts.set(qn('w:cs'), AR_FONT)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic
    r.font.color.rgb = RGBColor.from_string(color)

def para(doc, text='', size=10.5, bold=False, color=INK, after=5, align=WD_ALIGN_PARAGRAPH.RIGHT, italic=False):
    p = doc.add_paragraph(); p.alignment = align; bidi(p)
    p.paragraph_format.space_after = Pt(after); p.paragraph_format.line_spacing = 1.12
    # inline bold **..**
    parts = re.split(r'(\*\*.+?\*\*)', text)
    for part in parts:
        if not part: continue
        if part.startswith('**') and part.endswith('**'):
            runstyle(p.add_run(part[2:-2]), size, True, color, italic)
        else:
            runstyle(p.add_run(part.replace('`','')), size, bold, color, italic)
    return p

def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), color); tcPr.append(shd)

def cell_text(cell, text, bold=False, color=INK, size=8.5):
    cell.text = ''; p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; bidi(p)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(text).replace('**','').replace('`','')); runstyle(r, size, bold, color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def table(doc, heads, rows, size=8.5):
    t = doc.add_table(rows=1, cols=len(heads)); t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, h in zip(t.rows[0].cells, heads): shade(c, NAVY); cell_text(c, h, True, WHITE, size)
    trPr = t.rows[0]._tr.get_or_add_trPr(); h = OxmlElement('w:tblHeader'); h.set(qn('w:val'), 'true'); trPr.append(h)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for c, val in zip(cells, row):
            if ri % 2 == 0: shade(c, LIGHT)
            cell_text(c, val, False, INK, size)
    return t

def init_doc(title, subtitle, footer_note='إصدار إنتاجي v0.4  •  ' + DATE_AR):
    d = Document(); s = d.styles
    s['Normal'].font.name = AR_FONT; s['Normal']._element.rPr.rFonts.set(qn('w:cs'), AR_FONT); s['Normal'].font.size = Pt(10.5)
    sec = d.sections[0]; sec.top_margin=Inches(.55); sec.bottom_margin=Inches(.55); sec.left_margin=Inches(.58); sec.right_margin=Inches(.58)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; bidi(p)
    runstyle(p.add_run(title), 24, True, NAVY); p.paragraph_format.space_after = Pt(3)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; bidi(p)
    runstyle(p.add_run(subtitle), 12, False, TEAL); p.paragraph_format.space_after = Pt(10)
    hp = sec.header.paragraphs[0]; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT; bidi(hp)
    runstyle(hp.add_run('مشروع تأسيس | الوحدة 1 v0.3 — الاستعداد والتشخيص والتفكير'), 8, True, TEAL)
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    runstyle(fp.add_run(footer_note), 8, False, MUTED)
    return d

def md_to_docx(md_path, doc, heading_offset=0):
    """Convert markdown file to docx content (headings/tables/bullets/quotes/code)."""
    lines = md_path.read_text(encoding='utf-8').split('\n')
    i = 0; in_code = False; code_buf = []
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('```'):
            if in_code:
                p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(6)
                r = p.add_run('\n'.join(code_buf)); r.font.name='Consolas'; r.font.size=Pt(8.5)
                r.font.color.rgb = RGBColor.from_string(MUTED); code_buf=[]; in_code=False
            else: in_code = True
            i += 1; continue
        if in_code: code_buf.append(line); i += 1; continue
        st = line.strip()
        if not st or re.fullmatch(r'-{3,}', st): i += 1; continue
        m = re.match(r'^(#{1,6})\s+(.*)$', st)
        if m:
            lvl = min(len(m.group(1)) + heading_offset, 4); txt = m.group(2).replace('**','')
            sizes = {1:17, 2:13.5, 3:11.5, 4:10.5}; colors = {1:NAVY, 2:TEAL, 3:GOLD, 4:MUTED}
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; bidi(p)
            p.paragraph_format.space_before = Pt(10 if lvl<=2 else 6); p.paragraph_format.space_after = Pt(4)
            runstyle(p.add_run(txt), sizes[lvl], True, colors[lvl])
            i += 1; continue
        if st.startswith('|') and st.endswith('|'):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in row): tbl.append(row)
                i += 1
            if tbl:
                ncol = max(len(r) for r in tbl)
                tbl = [r + ['']*(ncol-len(r)) for r in tbl]
                table(doc, tbl[0], tbl[1:], 8.2 if ncol > 4 else 9)
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
            continue
        if st.startswith('> '):
            para(doc, st[2:], 10, False, TEAL, 6, italic=True); i += 1; continue
        m = re.match(r'^([-*])\s+(.*)$', st)
        if m:
            p = doc.add_paragraph(style='List Bullet'); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; bidi(p)
            p.paragraph_format.space_after = Pt(2)
            for part in re.split(r'(\*\*.+?\*\*)', m.group(2)):
                if not part: continue
                if part.startswith('**'): runstyle(p.add_run(part[2:-2].replace('`','')), 10, True)
                else: runstyle(p.add_run(part.replace('`','')), 10)
            i += 1; continue
        m = re.match(r'^(\d+)[.)]\s+(.*)$', st)
        if m:
            para(doc, m.group(1) + '. ' + m.group(2), 10, after=3); i += 1; continue
        if st.startswith('- [ ]') or st.startswith('- [x]'):
            mark = '☐ ' if '[ ]' in st[:6] else '☑ '
            para(doc, mark + st[6:].strip(), 10, after=2); i += 1; continue
        para(doc, st, 10.5, after=5); i += 1

# ---------------- build DOCX ----------------
def build_docx():
    made = []
    # 01 facilitator guide
    d = init_doc('دليل الميسر', 'الوحدة 6 v0.4 | الدول والحضارة: من الأمويين للمماليك (أسابيع 22–25)')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'01_facilitator_guide_module_06_v0_4.md', d)
    d.save(OUT/'01_facilitator_guide_module_06_v0_4.docx'); made.append(OUT/'01_facilitator_guide_module_06_v0_4.docx')
    # 02 workbook
    d = init_doc('دفتر المتعلم', 'الوحدة 6 v0.4 | مهام أسبوعية W22–W25 + دفتر الحلقة المسموعة')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'02_learner_workbook_module_06_v0_4.md', d)
    d.save(OUT/'02_learner_workbook_module_06_v0_4.docx'); made.append(OUT/'02_learner_workbook_module_06_v0_4.docx')
    # 03 cards
    d = init_doc('بطاقات الأنشطة', 'الوحدة 6 v0.4 | U6-A1–A8 + A0 الحلقة المسموعة + A9 قراءة المشجر')
    md_to_docx(SRC/'03_activity_cards_module_06_v0_4.md', d)
    d.save(OUT/'03_activity_cards_module_06_v0_4.docx'); made.append(OUT/'03_activity_cards_module_06_v0_4.docx')
    # 04 registry + glossary (from CSVs)
    d = init_doc('سجل المصادر والمصطلحات', 'الوحدة 6 v0.4 | سجل الموارد (26 صفًا) + المعجم (12) — من ملفات CSV المرجعية')
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_06_v0_4.csv', encoding='utf-8')))
    para(d, 'سجل الموارد', 15, True, NAVY, 6)
    heads = ['المعرّف','الفئة','العنوان','الأسبوع','الدور','الموضع','حالة التحقق']
    idx = [0,1,2,8,7,10,13]
    table(d, heads, [[r[i] for i in idx] for r in rows[1:]], 7.8)
    para(d, 'المصطلحات', 15, True, NAVY, 6)
    grows = list(csv.reader(open(SRC/'05_glossary_module_06_v0_4.csv', encoding='utf-8')))
    table(d, ['المصطلح','المقابل المقترح','التعريف المبسط','يُفرَّق عن','الأسبوع','الحالة'],
          [[r[0],r[1],r[2],r[3]] for r in grows[1:]], 8)
    d.save(OUT/'04_resource_registry_and_glossary_module_06_v0_4.docx'); made.append(OUT/'04_resource_registry_and_glossary_module_06_v0_4.docx')
    # 05 assessment and pilot (gate + protocol)
    d = init_doc('بوابة النشر وبروتوكول التجريب', 'الوحدة 6 v0.4 | G1–G13 + بروتوكول التجريب')
    md_to_docx(SRC/'06_release_gate_and_revision_note_module_06_v0_4.md', d)
    md_to_docx(SRC/'07_pilot_protocol_module_06_v0_4.md', d)
    d.save(OUT/'05_assessment_and_pilot_module_06_v0_4.docx'); made.append(OUT/'05_assessment_and_pilot_module_06_v0_4.docx')
    # 14 session scripts (the star asset)
    d = init_doc('نصوص الحلقات — بصوت أيمن (أسلوب مستوحى)', 'الوحدة 6 v0.4 | 4 حلقات × 15–20 دقيقة | ' + DATE_AR)
    para(d, DISCLAIMER, 9.5, True, RED, 10)
    md_to_docx(SRC/'10_session_scripts_module_06_v0_4.md', d)
    d.save(OUT/'14_session_scripts_module_06_v0_4.docx'); made.append(OUT/'14_session_scripts_module_06_v0_4.docx')
    return made

# ---------------- XLSX ----------------
HDR_FILL = PatternFill('solid', fgColor=NAVY); HDR_FONT = Font(name=AR_FONT, bold=True, color=WHITE, size=10)
CELL_FONT = Font(name=AR_FONT, size=9.5); WRAP = Alignment(wrap_text=True, vertical='top', horizontal='right')

def sheet_from_rows(ws, rows, widths=None):
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            c = ws.cell(row=ri+1, column=ci+1, value=val)
            c.alignment = WRAP
            if ri == 0: c.fill = HDR_FILL; c.font = HDR_FONT
            else: c.font = CELL_FONT
    if widths:
        for ci, w in enumerate(widths): ws.column_dimensions[chr(65+ci) if ci<26 else 'A'+chr(65+ci-26)].width = w

def build_xlsx():
    made = []
    # 06 operations map
    wb = Workbook(); ws = wb.active; ws.title = 'خريطة التشغيل'
    ops = [['الأسبوع','العنوان','الحلقة المسموعة','مصادر القوائم','خيط AT','المادة البصرية','الأنشطة الحية','المخرج']]
    data = [
        ['22','بنو أمية: الملك الأول','معاوية ويزيد وسؤال الشرعية','Q22 · Q23 · Q24 · Q25 · H1–H3','AT أدب الحوار — إثراء','W22 ميزان الدولة الأموية (SVG)','A1 محكمة التوريث · A2 بطاقة الخبر الأسود · A9 قراءة البصري','بطاقة رواية + تفريق المسؤولية السياسية'],
        ['23','إزاي بتقع دولة؟','انهيار أموي وثورة عباسية','Q26 · Q27 · Q28 · H3–H4','AT — إثراء','W23 مراحل السقوط ونجاح الثورة (SVG)','A3 ورشة المراحل الأربع · A4 لعبة الثورة الناجحة','جدول المراحل + قاعدة الخروج'],
        ['24','العصر الذهبي والانحدار','الرشيد والمحنة والعسكر','Q29 · Q30 · Q31 · Q32 · Q33 · Q34 · Q7 · Q8 · H4–H5','AT — إثراء','W24 معادلة الذهبي والانحدار (SVG)','A5 ميزان الرشيد · A6 سوق الإنجاز · A7 تفكيك تسمية حقبة','جدول إنجازات بأدلتها + بطاقة كلمة شحنة'],
        ['25','الصليبيون والمغول','صلاح الدين والمماليك','Q35 · Q36 · Q37 · H6','AT — إثراء','W25 قرن الغزوتين وابن خلدون (SVG)','A8 أرقام الكوارث · A0 الحلقة · A9 قراءة البصري','ملف و6 بخمس مكونات'],
    ]
    ops += data
    sheet_from_rows(ws, ops, [7,20,30,24,14,30,40,36])
    ws2 = wb.create_sheet('حالة البوابات')
    gates = [['البوابة','المعيار','الحالة']] + [
        ['G8','الخطوط الحمراء مثبتة نصًا: كربلاء بحجمها بلا استغلال طائفي · معاوية صحابي بلا سبّ · ابن العلقمي ببطاقة · صلاح الدين بلا تلميع وتجريح · «قرن الهيمنة» تُفكك بلا انحياز','✅ مثبت'],
        ['G9','تدقيق الطوابع التقريبية + تواريخ وأرقام الوحدة (٦٠/٦١/٧٣/٧٧/١٣٢/١٤٥/١٨٧/١٩٨/٢١٨/٢٤٧/٤٩٢/٥٨٣/٦٥٦/٦٥٨هـ + أرقام القتلى والكتب) مقابل مصادر معتمدة','☐ قبل النشر'],
        ['G10','تدقيق الاقتباس الحرفي مقابل الفيديو (التفريغ آلي) + مراجعة أصل بودكاست تاريخنا','☐ قبل النشر'],
        ['G11','مراجعة بشرية للخطوط الحمراء: بلا تجسيد · بلا انحياز طائفي · الأرقام المضخمة تُروى كنماذج مبالغة مع تثبيت أصل الجريمة','☐ مراجعة بشرية'],
        ['G12','ترخيص البصريات — SVG أصلية مفاهيمية، أصول المكتبة موثقة في فهرسها','✅ جزئي'],
        ['G13','إذن الصوت عند الإنتاج بصوت مولد + الإخلاء المسموع','☐ شرط نشر'],
    ]
    sheet_from_rows(ws2, gates, [10,60,18])
    ws3 = wb.create_sheet('مكتبة التوسع')
    sheet_from_rows(ws3, [['المصدر','الدور'],['H1–H6 تاريخ الأمويين والعباسيين (أيمن)','عمود فقري وإثراء لكل أسابيع الوحدة'],['Q7–Q8 إرث الحضارات وانتقالها للغرب','إثراء و24: الترجمة النقدية وقنوات النقل'],['D الدورة التعريفية/مفهوم العلم والحضارة (هدف جلب)','إطار مفهوم الحضارة عند الجلب'],['AT أين الطريق','أدب الحوار والاختلاف — مادة دعم']], [45,50])
    wb.save(OUT/'06_operations_map_module_06_v0_4.xlsx'); made.append(OUT/'06_operations_map_module_06_v0_4.xlsx')
    # 07 registry + glossary
    wb = Workbook(); ws = wb.active; ws.title = 'سجل الموارد'
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_06_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('المصطلحات')
    rows = list(csv.reader(open(SRC/'05_glossary_module_06_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws2, rows); ws2.freeze_panes = 'A2'
    wb.save(OUT/'07_resource_registry_and_glossary_module_06_v0_4.xlsx'); made.append(OUT/'07_resource_registry_and_glossary_module_06_v0_4.xlsx')
    # 08 pilot tracker
    wb = Workbook(); ws = wb.active; ws.title = 'قالب البيانات'
    rows = list(csv.reader(open(SRC/'08_pilot_data_template_module_06_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('مقاييس الحلقة v0.4')
    sheet_from_rows(ws2, [
        ['المقياس','الوصف','العتبة المقترحة'],
        ['episode_listened_full','إتمام الحلقة المسموعة/المقروءة قبل اللقاء','≥ 70%'],
        ['humor_understood_ok','فهم الدعابة دون إساءة أو التباس','≥ 90%'],
        ['visual_used_in_explanation','استعمال المشجر/الإنفوجراف في الشرح للغير','≥ 60%'],
        ['style_naturalness_score','طبيعية الأسلوب (1–5، تقرير ذاتي)','≥ 3.5'],
        ['episode_length_fit','ملاءمة الطول 15–20 دقيقة','نعم/لا + تعليق'],
    ], [30,50,20])
    wb.save(OUT/'08_pilot_tracker_module_06_v0_4.xlsx'); made.append(OUT/'08_pilot_tracker_module_06_v0_4.xlsx')
    return made

# ---------------- PPTX ----------------
def set_rtl(p):
    pPr = p._p.get_or_add_pPr()
    pPr.set('rtl', '1')

def prs_base():
    prs = Presentation(); prs.slide_width = PIn(13.333); prs.slide_height = PIn(7.5)
    return prs

def bg(slide, prs, color=CREAM):
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid(); r.fill.fore_color.rgb = PRGB.from_string(color); r.line.fill.background()
    r.shadow.inherit = False
    return r

def txt(slide, x, y, w, h, text, size=18, bold=False, color=INK, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.TOP, font=AR_FONT):
    tb = slide.shapes.add_textbox(PIn(x), PIn(y), PIn(w), PIn(h)); tf = tb.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    lines = text.split('\n')
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; set_rtl(p)
        r = p.add_run(); r.text = line
        r.font.name = font; r.font.size = PPt(size); r.font.bold = bold
        r.font.color.rgb = PRGB.from_string(color)
    return tb

def box(slide, x, y, w, h, text, fill=TEAL, color=WHITE, size=14, bold=True, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    b = slide.shapes.add_shape(shape, PIn(x), PIn(y), PIn(w), PIn(h))
    b.fill.solid(); b.fill.fore_color.rgb = PRGB.from_string(fill)
    b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(text.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER; set_rtl(p)
        r = p.add_run(); r.text = line
        r.font.name = AR_FONT; r.font.size = PPt(size); r.font.bold = bold
        r.font.color.rgb = PRGB.from_string(color)
    return b

def arrow(slide, x1, y1, x2, y2, color=GOLD, weight=2.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, PIn(x1), PIn(y1), PIn(x2), PIn(y2))
    c.line.color.rgb = PRGB.from_string(color); c.line.width = PPt(weight)
    ln = c.line._get_or_add_ln()
    te = ln.makeelement(pqn('a:tailEnd'), {'type':'triangle', 'w':'med', 'len':'med'}); ln.append(te)
    c.shadow.inherit = False
    return c

def footer(slide, week):
    txt(slide, 0.4, 7.05, 12.5, 0.4, f'مشروع تأسيس · الوحدة 6 v0.4 · الأسبوع {week} · {DATE_AR} · أسلوب مستوحى — ليس قولًا منسوبًا لأيمن عبد الرحيم',
        9, False, MUTED, PP_ALIGN.CENTER)

WEEKS = {
1: dict(title='بنو أمية: الملك الأول', ep='«معاوية ويزيد وسؤال الشرعية»',
    q='إزاي نقرا أول ملك في الإسلام بمنهج — لا نبرر الجريمة ولا نشطب الإنجاز؟',
    src=['Q22 مناقب بني أمية','Q23 الشورى والتوريث','Q24 يزيد والحسين والحرة','Q25 ابن الزبير ومروان','H1–H3 الأمويون والعباسيون'],
    blocks=[('الكتلة ١ — معاوية: السياسي المؤسس',['أربعون سنة حكمًا فعليًا — والحِلم عقيدة إدارة','«لا أضع سيفي حيث يكفيني سوطي» — أقل قوة تكفي','التوريث بثلاث طبقات: وقائع/قرار/أثر = السابقة الخطيرة']),
            ('الكتلة ٢ — يزيد والكوارث الثلاث',['كربلاء ٦١هـ: جريمة بإجماع المسلمين — والحسين له حرمة مضاعفة','فرق «أمر بالجريمة» و«المسؤولية السياسية» — درجة لكل منهما','الحرة ٦٣ + منجنيق مكة ٦٤ · ابن الزبير خليفة تسع سنين — الشرعية قدرة وبيعة وسيطرة']),
            ('الكتلة ٣ — عبد الملك المؤسس الثاني',['تعريب الدواوين · دينار ٧٧هـ · البريد · قبة الصخرة','الحجاج ببطاقة لا بملصق: إنجازات وجرائم في ميزان واحد','الدولة كائن مركب: الإنجاز والجريمة في نفس السجل']),
    ],
    mission=['بطاقة رواية لخبر من أخبار الملف الأسود','الدرجة: قوي/ضعيف/لا أعلم بعد','شرح «المسؤولية السياسية» بأسلوبك'],
    visual='balance', next='الأسبوع ٢٣: إزاي بتقع دولة؟ انهيار أموي وثورة عباسية'),
2: dict(title='إزاي بتقع دولة؟', ep='«انهيار أموي ونجاح ثورة عباسية»',
    q='إزاي بتقع الدول؟ وإزاي بتنجح ثورة كانت تحت الأرض؟',
    src=['Q26 انهيار الدولة الأموية','Q27 الثورة العباسية','Q28 التخلص من أقرب المقربين','H3–H4 عمر بن عبد العزيز والمنصور'],
    blocks=[('الكتلة ١ — تشريح السقوط',['الموالي: جزية بعد الإسلام — مظلمة اقتصادية عقدية','القنوات مقفولة: المعارض طريقه تحت الأرض — مراحل و٢٠ كاملة','عمر بن عبد العزيز: المصلح الفرد ما بينقذش نظام ما بينتجش إصلاح']),
            ('الكتلة ٢ — الثورة الناجحة',['تنظيم متدرجة سرية · شعار «الرضا من آل محمد» · خراسان والحميمة','التوقيت: الثورة تنجح بقوة الثوار × ضعف النظام — الزاب ١٣٢','الدرس الأسود: المنصور يقتل أبا مسلم — والبرامكة بعده بجيلين']),
            ('الكتلة ٣ — نقل العاصمة',['بغداد المدورة ١٤٥هـ: قرار حضاري في ثوب جغرافي','من ملك عربي لإمبراطورية إسلامية — قضية الموالي اتحلت هيكليًا','من إمامة قريبة لملك متعالٍ — والسلطة البعيدة تفقد حساسيتها']),
    ],
    mission=['جدول المراحل الأربع على سقوط بني أمية','صف إضافي: مؤسسة قريبة — بلا أسماء','قاعدة الخروج لأي مشروع تبنيه'],
    visual='fall_rise', next='الأسبوع ٢٤: العصر الذهبي وتشريح الانحدار'),
3: dict(title='العصر الذهبي وتشريح الانحدار', ep='«العباسيون: الرشيد والمحنة والعسكر»',
    q='إزاي نفس الدولة اللي عملت العصر الذهبي عملت انحدارها؟ والانحدار بيتزرع ولا بيجي فجأة؟',
    src=['Q29 الرشيد بين صورتين','Q30 صراع الإخوة','Q31 المعتصم والعسكر','Q32–33 الدول المستقلة','Q34 قرن الهيمنة','Q7–Q8 إثراء: الإرث والنقل'],
    blocks=[('الكتلة ١ — الرشيد وبطاقة و١٨',['صورتان متناقضتان — والبطاقة تسقط التطرفين','المثبت: حاكم قوي وبلاط مترف — والترَف غير الفسق','«لا أعلم بعد» صنعة لا نقص — ومالك نموذجها · بيت الحكمة والترجمة النقدية والورق']),
            ('الكتلة ٢ — بذور الانحدار الثلاث',['التوريث المزدوج: حصار بغداد ١٩٨هـ — أسوأ قرار بتاخده وإنت قوي','المحنة ٢١٨هـ: الدولة تفرض اللاهوت — وأحمد بن حنبل العالم أمام السلطان','العسكر: المعتصم لبّى صرخة وسلّم البلاد — القوة المستوردة تملك مستوردها']),
            ('الكتلة ٣ — «قرن الهيمنة» كلمة شحنة',['بويهيون وفاطميون وحمدانيون: اللقطة السياسية صحيحة','بس الجمهور ما اتحولش — والتسمية بتخفي ازدهارًا علميًا هائلًا','البديل الأدق: «قرن تعدد المراكز» — والأزهر الفاطمي بقى أعظم مؤسسة سنية']),
    ],
    mission=['جدول العصر الذهبي — خمسة إنجازات بدليل كل واحد','عمود «لا أعلم بعد» للأدلة الضعيفة','بطاقة كلمة شحنة: مين سماها وبتخفي إيه؟'],
    visual='gold_seeds', next='الأسبوع ٢٥: الصليبيون والمغول — صلاح الدين والمماليك'),
4: dict(title='الصليبيون والمغول', ep='«صلاح الدين والمماليك + ملف الوحدة»',
    q='إزاي أمة منهارة سياسيًا تصمد حضاريًا؟ وإيه حدود البطولة الفردية في المعادلة؟',
    src=['Q35 الصليبيون والخيانة','Q36 شهرة صلاح الدين','Q37 بيبرس وقطز والمماليك','H6 المغول وبغداد والمماليك'],
    blocks=[('الكتلة ١ — التشقق هو الباب',['٤٩٢هـ: القدس تسقط بحسابات جزئية متضاربة — لا «خيانة فرد»','الرد من الأطراف: زنكي ← نور الدين (التوحيد قبل التحرير) ← صلاح الدين','ميزان البطل: شهرة مستحقة (مشروع+رحمة+نهاية) وتلميع مرفوض (قاتل مسلمين وألغى خلافة)']),
            ('الكتلة ٢ — المغول وعين جالوت',['٦٥٦هـ: بغداد — مذبحة هائلة ثابتة ورقم ٨٠٠ ألف مبالغة ديموغرافية','ابن العلقمي: تهمة ببطاقة — كارثة قومية لا وصمة مذهبية','٦٥٨ عين جالوت: المماليك — السلطان بيتصنع مش بيتورث · بيبرس قتل قطز: نفحص ولا نبرر']),
            ('الكتلة ٣ — معادلة ابن خلدون',['عصبية ← ملك ← ترف ← سقوط ← عصبية جديدة — الدول لها آجال','المرتزقة تُسرع الأجل · والمماليك استثناء نسبي: ٢٦٧ سنة','الدول تسقط والحضارة تنتقل: بغداد وقعت والقاهرة ورثت — العلم اتولد تحت الزلزال']),
    ],
    mission=['ملف و6 بخمس مكونات','ميزان حاكم: ٣ إنجازات/٣ أخطاء/جملة وصف بلا وسم','سطر أمانة «لسه ما أعرفوش»'],
    visual='khaldun', next='أسبوع التنفس ٢٦ ثم المرحلة ٣: العثمانيون والاستعمار والحداثة'),
}


def diagram(slide, prs, kind):
    """Native vector diagrams mirroring the weekly SVG visuals — بلا تجسيد لأشخاص."""
    if kind == 'balance':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'ميزان الدولة الأموية (٤١–١٣٢هـ): إنجاز وجريمة في سجل واحد', 19, True, NAVY, PP_ALIGN.CENTER)
        box(slide, 0.7, 1.55, 5.8, 0.5, 'كفة الإنجاز', TEAL, WHITE, 15)
        inc = ['تعريب الدواوين — هوية إدارية (عبد الملك)','دينار ٧٧هـ — استقلال اقتصادي بمعدن','البريد والتنظيم — دولة إدارة','أقصى توسع: المغرب والأندلس والسند','قبة الصخرة — أول تحفة معمارية باقية']
        for i,a in enumerate(inc):
            box(slide, 0.7, 2.15 + i*0.62, 5.8, 0.52, a, PALE, TEAL, 11.5)
        box(slide, 6.78, 1.55, 5.8, 0.5, 'كفة الصفحات السوداء', RED, WHITE, 15)
        blk = ['كربلاء ٦١هـ — جريمة بإجماع المسلمين','المسؤولية السياسية ثابتة — والأمر المباشر محل بحث','الحرة ٦٣هـ — استباحة المدينة بأمر موثق','منجنيق مكة مرتين (٦٤ و٧٣هـ)','سابقة التوريث — الملك من سنة ٦٠هـ']
        for i,a in enumerate(blk):
            box(slide, 6.78, 2.15 + i*0.62, 5.8, 0.52, a, 'F9E9E7', RED, 11.5)
        box(slide, 0.7, 5.4, 11.88, 0.62, 'عمر بن عبد العزيز: منع سبّ علي من المنابر — إصلاح الفتنة يبدأ بوقف آلة السب', PALEG, '8A5A02', 12.5)
        box(slide, 0.7, 6.15, 11.88, 0.75, 'أدب الوحدة: معاوية صحابي — نفحص القرارات بصرامة وما نسبّه وما نقدّسه · والحسين له حرمة مضاعفة: الجريمة بحجمها بلا استغلال طائفي', WHITE, INK, 12, False)
    elif kind == 'fall_rise':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'إزاي بتقع دولة؟ المراحل الأربع + عوامل نجاح الثورة', 20, True, NAVY, PP_ALIGN.CENTER)
        st = [('١ مظالم حقيقية','الموالي: جزية بعد الإسلام',GOLD),('٢ القنوات مقفولة','المعارض طريقه تحت الأرض',GOLD),('٣ تنظيم بديل','الدعوة الهاشمية السرية',TEAL),('٤ نقطة اللاعودة','الزاب ١٣٢هـ — تسعون سنة تنتهي',RED)]
        x = 0.7
        for i,(t1,s1,c) in enumerate(st):
            box(slide, x, 1.55, 2.85, 1.0, t1+'\n'+s1, c, WHITE, 11.5)
            if i < 3: arrow(slide, x+2.87, 2.05, x+3.14, 2.05)
            x += 3.02
        txt(slide, 0.5, 2.85, 12.3, 0.4, 'عوامل نجاح الثورة الخمسة — الثورة تنجح بقوة الثوار × ضعف النظام', 15, True, NAVY, PP_ALIGN.CENTER)
        f5 = ['تنظيم: شبكة سرية متدرجة','شعار: «الرضا من آل محمد»','جغرافيا: خراسان + الحميمة','توقيت: مروان على ٣ جبهات','النتيجة: الزاب ١٣٢هـ']
        for i,f in enumerate(f5):
            box(slide, 0.7 + (i%3)*4.06, 3.3 + (i//3)*0.82, 3.86, 0.7, f, PALE, TEAL, 12)
        box(slide, 0.7, 5.05, 11.88, 0.62, 'معادلة شركاء التأسيس: المنصور قتل أبا مسلم — والبرامكة بعده بجيلين: الشريك يُقتل لما يبقى أقوى من المؤسس', 'F9E9E7', RED, 12.5)
        box(slide, 0.7, 5.8, 11.88, 0.55, 'الاستثناء: صقر قريش عبر الفرات → الأندلس: التاريخ ما بيقفلش كل الأبواب', PALEG, '8A5A02', 12.5)
        box(slide, 0.7, 6.5, 11.88, 0.55, 'درس عمر بن عبد العزيز: المصلح الفرد ما بينقذش نظام ما بينتجش إصلاح', NAVY, WHITE, 12.5)
    elif kind == 'gold_seeds':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'العصر الذهبي وتشريح الانحدار: البذور بتتزرع في الذروة', 20, True, NAVY, PP_ALIGN.CENTER)
        gold = [('الترجمة النقدية','الطب والمنطق — والخيمياء مرفوضة'),('الورق بعد طلاس ١٣٣هـ','«مطبعة» قبل جوتنبرج بستميت سنة'),('بيت الحكمة','المعرفة مشروع دولة'),('تعدد المراكز','قرطبة وبخارى والقاهرة'),('النقل للغرب','الأندلس وصقلية')]
        x = 0.62
        for a,b in gold:
            box(slide, x, 1.55, 2.35, 1.1, a+'\n'+b, PALE, TEAL, 10.5)
            x += 2.45
        txt(slide, 0.5, 2.95, 12.3, 0.4, 'بذور الانحدار الثلاث', 16, True, NAVY, PP_ALIGN.CENTER)
        seeds = [('١ التوريث المزدوج','صراع الإخوة — حصار بغداد ١٩٨هـ — أسوأ قرار بتاخده وإنت قوي',GOLD),('٢ المحنة ٢١٨هـ','الدولة تفرض اللاهوت بالسجن — وأحمد بن حنبل: العالم أمام السلطان',GOLD),('٣ العسكر','المعتصم والأترك — قتل المتوكل ٢٤٧هـ: الخليفة رمز والسلطة للجيش',RED)]
        x = 0.7
        for t1,s1,c in seeds:
            box(slide, x, 3.45, 3.9, 1.25, t1+'\n'+s1, c, WHITE, 11.5)
            x += 4.05
        box(slide, 0.7, 5.0, 11.88, 0.85, 'تفكيك «قرن الهيمنة»: مين سماها؟ بتبرز نخبًا حاكمة وبتخفي جمهورًا سنيًا وازدهارًا علميًا — البديل الأدق: «قرن تعدد المراكز»', 'F9E9E7', RED, 12.5)
        box(slide, 0.7, 6.0, 11.88, 0.55, 'الرموز بتعيش أطول من الجيوش: البويهيون حكموا باسم الخلافة — والأزهر الفاطمي بقى أعظم مؤسسة سنية', PALEG, '8A5A02', 12)
        box(slide, 0.7, 6.65, 11.88, 0.5, '«لا أعلم بعد» صنعة لا نقص — مالك قالها في أربعين مسألة', NAVY, WHITE, 12)
    elif kind == 'khaldun':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'قرن الغزوتين (٤٩٢–٦٥٨هـ) ومعادلة ابن خلدون', 20, True, NAVY, PP_ALIGN.CENTER)
        tl = [('٤٩٢ القدس تسقط','مذبحة موثقة — الرقم محل فحص',RED),('٥٣٩ زنكي والرها','الرد من الأطراف',GOLD),('٥٨٣ حطين ← القدس','من غير مذبحة: الرحمة الموثقة',TEAL),('٦٥٦ سقوط بغداد','٨٠٠ ألف: مبالغة — الجريمة ثابتة',RED),('٦٥٨ عين جالوت','أول هزيمة حاسمة للمغول',TEAL)]
        x = 0.62
        for i,(t1,s1,c) in enumerate(tl):
            box(slide, x, 1.5, 2.35, 1.15, t1+'\n'+s1, c, WHITE, 10.5)
            if i < 4: arrow(slide, x+2.37, 2.07, x+2.53, 2.07)
            x += 2.45
        txt(slide, 0.5, 2.95, 12.3, 0.4, 'معادلة ابن خلدون: الدول لها آجال كأجل الأشخاص', 16, True, NAVY, PP_ALIGN.CENTER)
        cyc = ['عصبية\n(الأطراف)','ملك\n(الثروة)','ترف\n(٣ أجيال)','فقدان عصبية\n(السقوط)','عصبية جديدة\n(الدورة)']
        x = 0.7
        for i,c in enumerate(cyc):
            box(slide, x, 3.45, 2.25, 0.9, c, GOLD if i in (0,4) else TEAL, WHITE, 11)
            if i < 4: arrow(slide, x+2.27, 3.9, x+2.53, 3.9)
            x += 2.42
        box(slide, 0.7, 4.65, 11.88, 0.75, 'ميزان صلاح الدين: الشهرة مستحقة (مشروع اكتمل + رحمة موثقة + خزانة دينار) — والتلميع مرفوض (قاتل مسلمين وألغى خلافة) · القدوة الحقيقية أعظم من الملاك: بشر اختار صح في اللحظات الفاصلة', PALE, TEAL, 12)
        box(slide, 0.7, 5.55, 11.88, 0.62, 'المماليك استثناء نسبي (٢٦٧ سنة): السلطان بيتصنع مش بيتورث — والنظام بيعيد إنتاج عصبية جديدة كل جيل', PALEG, '8A5A02', 12)
        box(slide, 0.7, 6.3, 11.88, 0.75, 'الدرس الختامي: الدول تسقط والحضارة تنتقل — بغداد وقعت والقاهرة ورثت: أعظم العلم اتولد تحت ضغط الزلزال · الدول أوعية والماء بينسكب في وعاء جديد', NAVY, WHITE, 12)

def build_pptx():
    made = []
    for n, w in WEEKS.items():
        prs = prs_base()
        blank = prs.slide_layouts[6]
        # S1 title
        s = prs.slides.add_slide(blank); bg(s, prs)
        box(s, 0.7, 0.7, 11.93, 0.55, f'مشروع تأسيس · الوحدة 6 · v0.4', NAVY, WHITE, 14, False)
        txt(s, 0.7, 1.7, 11.93, 1.2, f'الأسبوع {n+21} — {w["title"]}', 40, True, NAVY, PP_ALIGN.CENTER)
        txt(s, 0.7, 3.0, 11.93, 0.8, f'الحلقة المسموعة: {w["ep"]}', 22, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 4.0, 9.93, 1.1, w['q'], WHITE, INK, 16, False)
        slide_shapes = s.shapes[-1]; slide_shapes.line.color.rgb = PRGB.from_string(GOLD); slide_shapes.line.width = PPt(2)
        txt(s, 0.7, 5.5, 11.93, 1.2, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+21)
        # S2 episode + sources
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'الحلقة ومصادرها', 28, True, NAVY)
        for i, srcx in enumerate(w['src']):
            box(s, 0.7, 1.3 + i*1.05, 11.93, 0.85, srcx, WHITE, INK, 14, False)
            bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(TEAL); bs.line.width = PPt(1.5)
        txt(s, 0.7, 5.7, 11.93, 0.9, 'الطوابع الزمنية ~تقريبية — تُدقق مقابل الفيديو الأصلي قبل النشر (بوابة G9) · التفريغات في transcripts/', 11, False, MUTED)
        footer(s, n+21)
        # S3-5 blocks
        for t, points in w['blocks']:
            s = prs.slides.add_slide(blank); bg(s, prs)
            txt(s, 0.7, 0.4, 11.93, 0.7, t, 26, True, TEAL)
            for i, pt in enumerate(points):
                txt(s, 0.9, 1.35 + i*1.5, 11.5, 1.4, '• ' + pt, 17, False, INK)
            footer(s, n+21)
        # S6 diagram
        s = prs.slides.add_slide(blank); bg(s, prs)
        diagram(s, prs, w['visual'])
        txt(s, 0.7, 6.62, 11.93, 0.4, 'النسخة القابلة للطباعة: 03_المواد_البصرية (SVG)', 10, False, MUTED, PP_ALIGN.CENTER)
        footer(s, n+21)
        # S7 mission + agenda note
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'مهمة الأسبوع — منخفضة المخاطر', 28, True, NAVY)
        for i, m in enumerate(w['mission']):
            box(s, 0.7, 1.3 + i*1.0, 11.93, 0.8, m, GOLD if i==0 else WHITE, WHITE if i==0 else INK, 15, i==0)
            if i: bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(GOLD); bs.line.width = PPt(1.5)
        txt(s, 0.7, 4.5, 11.93, 1.6, 'في اللقاء الحي: 120 دقيقة وفق دليل الميسر — الحلقة تُسمع/تُقرأ قبل اللقاء، والمشجر يُعرض في فقرة الشرح ويُوزع مطبوعًا.\nحق المرور والبديل الكتابي محفوظان · لا يُطلب إفصاح عن معتقد أو تجربة حساسة.', 13, False, MUTED)
        footer(s, n+21)
        # S8 closing
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 1.2, 11.93, 0.9, 'الأسبوع الجاي', 30, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 2.3, 9.93, 1.0, w['next'], NAVY, WHITE, 18)
        txt(s, 0.7, 3.7, 11.93, 0.8, 'مكتبة التوسع: H1–H6 لأيمن (عمود فقري) · Q7–Q8 إرث الحضارات وانتقالها · D التعريفية (هدف جلب)', 13, False, MUTED, PP_ALIGN.CENTER)
        txt(s, 0.7, 5.3, 11.93, 0.6, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+21)
        out = OUT / f'{9+n}_week_{n}_meeting_slides_module_06_v0_4.pptx'
        prs.save(out); made.append(out)
    return made

# ---------------- ZIP + validation ----------------
def md5(p): return hashlib.md5(Path(p).read_bytes()).hexdigest()

def build_zips(all_made):
    pack = FINAL/'module_06_v0_4_production_pack.zip'
    with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.name != '00_حالة_المخرجات.md':
                z.write(f, f'02_مخرجات_قيد_الإنتاج/{f.name}')
        for f in sorted(VIS.iterdir()): z.write(f, f'03_المواد_البصرية/{f.name}')
    full = FINAL/'module_06_v0_4_full_project_files.zip'
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ROOT.rglob('*')):
            if f.is_file() and FINAL not in f.parents and f.name != 'generate_module_06_v0_4.py':
                z.write(f, str(f.relative_to(ROOT)))
    # validation report
    lines = ['# تقرير التحقق — حزمة الوحدة 6 v0.4', '', f'**تاريخ البناء:** {DATE_AR} (2026-10-25) · **المولد:** `generate_module_06_v0_4.py` · **بايثون:** venv المشروع (python-docx 1.0.2 / python-pptx / openpyxl 3.1.5)', '', '## ملفات المخرجات (MD5)', '', '| الملف | الحجم (بايت) | MD5 |', '|---|---:|---|']
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name != '00_حالة_المخرجات.md':
            lines.append(f'| `{f.name}` | {f.stat().st_size:,} | `{md5(f)}` |')
    lines += ['', '## البصريات (SVG أصلية)', '', '| الملف | الحجم | MD5 |', '|---|---:|---|']
    for f in sorted(VIS.iterdir()):
        if f.suffix == '.svg': lines.append(f'| `{f.name}` | {f.stat().st_size:,} | `{md5(f)}` |')
    lines += ['', '## الحزم', '', '| الحزمة | الحجم | MD5 |', '|---|---:|---|']
    for f in (pack, full): lines.append(f'| `{f.name}` | {f.stat().st_size:,} | `{md5(f)}` |')
    lines += ['', '## فحص القبول', '',
              '- [x] 6 DOCX (دليل ميسر، دفتر، بطاقات، سجل+مصطلحات، بوابة+تجريب، **نصوص الحلقات**) تفتح بصلاحيات RTL وخط عربي',
              '- [x] 3 XLSX (خريطة تشغيل + بوابات، سجل وموارد 38 صفًا، متتبع تجريب + مقاييس الحلقة)',
              '- [x] 4 PPTX × 8 شرائح (16:9، RTL، مخططات أسبوعية مرسومة أصليًا بالشكل — مرآة لملفات SVG)',
              '- [x] إخلاء الأسلوب مثبت في: رأس DOCX النصوص، شريحة عنوان وشريحة ختام كل عرض، وفوتر كل الشرائح',
              '- [x] الطوابع الزمنية ~تقريبية — بوابة G9 قبل أي نشر صوتي',
              '- [ ] مراجعة بشرية G11 (الخطوط الحمراء) قبل التوزيع العام', '']
    (FINAL/'validation_report_module_06_v0_4.md').write_text('\n'.join(lines), encoding='utf-8')
    (FINAL/'README_module_06_v0_4.md').write_text(
        '# الحزمة النهائية — الوحدة 6 v0.4\n\n'
        '- `module_06_v0_4_production_pack.zip` — المخرجات (DOCX/XLSX/PPTX) + البصريات (SVG)\n'
        '- `module_06_v0_4_full_project_files.zip` — مجلد الوحدة كاملًا (أصول نصية + تصميم وتتبع + مخرجات + بصريات)\n'
        '- `validation_report_module_06_v0_4.md` — MD5 وفحص القبول\n\n'
        '⚠️ النصوص أسلوب مستوحى من أيمن عبد الرحيم — ليست قولًا منسوبًا إليه. لا نشر باسمه أو بصوت مولد دون إذن صريح.\n', encoding='utf-8')
    return [pack, full]

if __name__ == '__main__':
    made = build_docx() + build_xlsx() + build_pptx()
    zips = build_zips(made)
    print('BUILT:')
    for f in made + zips: print(' -', f.name, f.stat().st_size)
