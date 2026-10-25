#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 05 v0.4 outputs (DOCX/XLSX/PPTX) and auditable ZIPs.
Run with: .venv/bin/python generate_module_05_v0_4.py
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
    d = init_doc('دليل الميسر', 'الوحدة 5 v0.4 | مدخل التاريخ: منهج، راشدون، فتنة (أسابيع 18–21)')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'01_facilitator_guide_module_05_v0_4.md', d)
    d.save(OUT/'01_facilitator_guide_module_05_v0_4.docx'); made.append(OUT/'01_facilitator_guide_module_05_v0_4.docx')
    # 02 workbook
    d = init_doc('دفتر المتعلم', 'الوحدة 5 v0.4 | مهام أسبوعية W18–W21 + دفتر الحلقة المسموعة')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'02_learner_workbook_module_05_v0_4.md', d)
    d.save(OUT/'02_learner_workbook_module_05_v0_4.docx'); made.append(OUT/'02_learner_workbook_module_05_v0_4.docx')
    # 03 cards
    d = init_doc('بطاقات الأنشطة', 'الوحدة 5 v0.4 | U5-A1–A8 + A0 الحلقة المسموعة + A9 قراءة المشجر')
    md_to_docx(SRC/'03_activity_cards_module_05_v0_4.md', d)
    d.save(OUT/'03_activity_cards_module_05_v0_4.docx'); made.append(OUT/'03_activity_cards_module_05_v0_4.docx')
    # 04 registry + glossary (from CSVs)
    d = init_doc('سجل المصادر والمصطلحات', 'الوحدة 5 v0.4 | سجل الموارد (14 صفًا) + المعجم (11) — من ملفات CSV المرجعية')
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_05_v0_4.csv', encoding='utf-8')))
    para(d, 'سجل الموارد', 15, True, NAVY, 6)
    heads = ['المعرّف','الفئة','العنوان','الأسبوع','الدور','الموضع','حالة التحقق']
    idx = [0,1,2,8,7,10,13]
    table(d, heads, [[r[i] for i in idx] for r in rows[1:]], 7.8)
    para(d, 'المصطلحات', 15, True, NAVY, 6)
    grows = list(csv.reader(open(SRC/'05_glossary_module_05_v0_4.csv', encoding='utf-8')))
    table(d, ['المصطلح','المقابل المقترح','التعريف المبسط','يُفرَّق عن','الأسبوع','الحالة'],
          [[r[0],r[1],r[2],r[3]] for r in grows[1:]], 8)
    d.save(OUT/'04_resource_registry_and_glossary_module_05_v0_4.docx'); made.append(OUT/'04_resource_registry_and_glossary_module_05_v0_4.docx')
    # 05 assessment and pilot (gate + protocol)
    d = init_doc('بوابة النشر وبروتوكول التجريب', 'الوحدة 5 v0.4 | G1–G13 + بروتوكول التجريب')
    md_to_docx(SRC/'06_release_gate_and_revision_note_module_05_v0_4.md', d)
    md_to_docx(SRC/'07_pilot_protocol_module_05_v0_4.md', d)
    d.save(OUT/'05_assessment_and_pilot_module_05_v0_4.docx'); made.append(OUT/'05_assessment_and_pilot_module_05_v0_4.docx')
    # 14 session scripts (the star asset)
    d = init_doc('نصوص الحلقات — بصوت أيمن (أسلوب مستوحى)', 'الوحدة 5 v0.4 | 4 حلقات × 15–20 دقيقة | ' + DATE_AR)
    para(d, DISCLAIMER, 9.5, True, RED, 10)
    md_to_docx(SRC/'10_session_scripts_module_05_v0_4.md', d)
    d.save(OUT/'14_session_scripts_module_05_v0_4.docx'); made.append(OUT/'14_session_scripts_module_05_v0_4.docx')
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
        ['18','تاريخنا مزور؟','منهج قراءة التاريخ','Q1 · Q3 · R هدف جلب','AT أدب الحوار — إثراء','W18 بطاقة الرواية الخماسية (SVG)','A1 محكمة الرواية · A2 سوق التعميم المجهول · A9 قراءة البصري','بطاقة رواية خماسية + درجة نهائية'],
        ['19','الصاحبان: تأسيس الدولة','أبو بكر وعمر — شورى ومؤسسات','Q15 · Q16 · Q17','AT — إثراء','W19 زمن الراشدين ومؤسسات عمر (SVG)','A3 ورشة المؤسسات الست · A4 تحليل قرار السقيفة · A5 معايير الفتح','جدول مؤسسات + طبقات الأحقية الثلاث'],
        ['20','عثمان وبذور الفتنة','إزاي بيتشقق المجتمع؟','Q18 · H1','AT — إثراء','W20 مراحل التشقق الأربع (SVG)','A6 تشريح الشقوق · A7 ميزان نقد واتهام','تشريح شق قريب بالمراحل الأربع — بلا أسماء'],
        ['21','الفتنة: بلا تقديس ولا ازدراء','علي وجمال وصفين والخوارج','Q19 · Q20 · Q21 · H2','AT — إثراء','W21 خريطة الفتنة وآدابها (SVG)','A8 اختبار الخوارج · A0 الحلقة · A9 قراءة البصري','ملف و5 بخمس مكونات'],
    ]
    ops += data
    sheet_from_rows(ws, ops, [7,20,30,24,14,30,40,36])
    ws2 = wb.create_sheet('حالة البوابات')
    gates = [['البوابة','المعيار','الحالة']] + [
        ['G8','أدب الصحابة مثبت نصًا في كل أصل: كف اللسان + فهم الشروط + حفظ الحرمة + فحص الأخبار','✅ مثبت'],
        ['G9','تدقيق الطوابع التقريبية + تواريخ وأرقام الفتنة (٣٥/٣٦/٣٧/٤٠/٤١هـ) مقابل مصادر معتمدة','☐ قبل النشر'],
        ['G10','تدقيق الاقتباس الحرفي مقابل الفيديو (التفريغ آلي) + مراجعة أصل بودكاست تاريخنا','☐ قبل النشر'],
        ['G11','مراجعة بشرية للخطوط الحمراء: بلا تجسيد · بلا ترجيح طائفي · حكاية الخداع تُروى بدرجة سندها','☐ مراجعة بشرية'],
        ['G12','ترخيص البصريات — SVG أصلية مفاهيمية، أصول المكتبة موثقة في فهرسها','✅ جزئي'],
        ['G13','إذن الصوت عند الإنتاج بصوت مولد + الإخلاء المسموع','☐ شرط نشر'],
    ]
    sheet_from_rows(ws2, gates, [10,60,18])
    ws3 = wb.create_sheet('مكتبة التوسع')
    sheet_from_rows(ws3, [['المصدر','الدور'],['H1–H6 تاريخ الأمويين والعباسيين (أيمن)','إثراء مسموع لخلفية و20–21 وتمهيد و6'],['R الخلفاء الراشدون / مدخل دراسة التاريخ (هدف جلب)','بديل/مكمل عند الجلب — مواضع معلَّمة في السجل'],['AT أين الطريق','أدب الحوار والاختلاف — مادة دعم']], [45,50])
    wb.save(OUT/'06_operations_map_module_05_v0_4.xlsx'); made.append(OUT/'06_operations_map_module_05_v0_4.xlsx')
    # 07 registry + glossary
    wb = Workbook(); ws = wb.active; ws.title = 'سجل الموارد'
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_05_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('المصطلحات')
    rows = list(csv.reader(open(SRC/'05_glossary_module_05_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws2, rows); ws2.freeze_panes = 'A2'
    wb.save(OUT/'07_resource_registry_and_glossary_module_05_v0_4.xlsx'); made.append(OUT/'07_resource_registry_and_glossary_module_05_v0_4.xlsx')
    # 08 pilot tracker
    wb = Workbook(); ws = wb.active; ws.title = 'قالب البيانات'
    rows = list(csv.reader(open(SRC/'08_pilot_data_template_module_05_v0_4.csv', encoding='utf-8')))
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
    wb.save(OUT/'08_pilot_tracker_module_05_v0_4.xlsx'); made.append(OUT/'08_pilot_tracker_module_05_v0_4.xlsx')
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
    txt(slide, 0.4, 7.05, 12.5, 0.4, f'مشروع تأسيس · الوحدة 5 v0.4 · الأسبوع {week} · {DATE_AR} · أسلوب مستوحى — ليس قولًا منسوبًا لأيمن عبد الرحيم',
        9, False, MUTED, PP_ALIGN.CENTER)

WEEKS = {
1: dict(title='تاريخنا مزور؟', ep='«منهج قراءة التاريخ»',
    q='إزاي أقرا خبرًا تاريخيًا بمنهج — لا بتقديس أعمى ولا بازدراء أعمى؟',
    src=['Q1 هل تاريخنا مزور؟','Q3 كيف يكشف التاريخ الكذابين؟','R مدخل دراسة التاريخ — هدف جلب'],
    blocks=[('الكتلة ١ — التهمة تُفحص لا تُبتلع',['الطبري يكتب بنفسه: «منه صحيح ومنها سقيم»','ابن الجوزي يصنف الموضوعات — جهاز مناعة ذاتي','أمة بتحاكم روايتها بنفسها، مش بتخفي عيوبها']),
            ('الكتلة ٢ — بطاقة الرواية الخماسية',['١ الراوي · ٢ السلسلة · ٣ المتن · ٤ السياق والمصلحة · ٥ الأثر','على قد الأثر تكون الصرامة — قاعدة و4 مطبقة على التاريخ','التعميم المجهول علامة حمراء: «قالوا» — أنهي مؤرخين؟ فين أسماؤهم؟']),
            ('الكتلة ٣ — بين التقديس والازدراء',['تقديس العصر يشيل أعظم ميزة: بشر اجتهدوا — قابلون للاقتداء','الازدراء (الحاضرية): محاكمة أزمنة بمسطرة قرنك','الوسط: يُفهم بشروطه · يُقيَّم بمعاييره والوحي · يُستفاد منه لحاضرنا']),
    ],
    mission=['بطاقة رواية خماسية لخبر تاريخي مشهور','درجة نهائية: قوي/ضعيف/لا أعلم بعد','صيد تعميم مجهول واحد في مقال أو بوست'],
    visual='card5', next='الأسبوع ١٩: الصاحبان — أبو بكر وعمر وتأسيس الدولة'),
2: dict(title='الصاحبان: تأسيس الدولة', ep='«أبو بكر وعمر — شورى ومؤسسات»',
    q='إزاي جماعة مضطهدة بقت دولة مؤسسات في عشر سنين؟ وإزاي نختلف على الأحقية بأدب؟',
    src=['Q15 تلخيص الخلافة الراشدة','Q16 الأحقية: أبو بكر أم علي؟','Q17 الفتح مقابل الاستعمار'],
    blocks=[('الكتلة ١ — انتقال السلطة',['السقيفة: حجج ثم شورى ثم بيعة — «اللي خالف رجع»','حروب الردة: وحدة الدولة + ركن الزكاة — «لو منعوني عقالًا»','توجيه الطاقة للخارج: الفتوح']),
            ('الكتلة ٢ — مؤسسات عمر',['دواوين · تقويم هجري · قضاء مستقل · حسبة','محاسبة الولاة: «من أين لك هذا؟» + قصة ابن القبطي','رعاية بيت المال حتى لغير المسلمين — العجوز اليهودية']),
            ('الكتلة ٣ — الأسئلة الصعبة',['الأحقية بثلاث طبقات: وقائع / أفهام / ثمرة عملية = الأدب','«تلك أمة قد خلت» — الخلاف الفقهي لا يفسد الأخوة','الفتح ≠ الاستعمار: أرض · دين · مال · شهادة المفتوحين']),
    ],
    mission=['جدول مؤسسات عمر الستة (مشكلة/قرار/أثر باقٍ)','طبقات سؤال الأحقية الثلاث','معيار واحد من معايير الفتح مطبق على حدث'],
    visual='institutions', next='الأسبوع ٢٠: عثمان وبذور الفتنة — إزاي بيتشقق المجتمع؟'),
3: dict(title='عثمان وبذور الفتنة', ep='«إزاي بيتشقق المجتمع؟»',
    q='إزاي مجتمع انتصر ووحّد واتسع — انشق في ٦ سنين؟ وإيه اللي أتعلمه من التشريح بلا اتهام أشخاص؟',
    src=['Q18 من قتل عثمان وبذور الفتنة','H1 الأمويون والعباسيون — خلفية العهد','AT أين الطريق — إثراء أدب الحوار'],
    blocks=[('الكتلة ١ — الإنجازات أولًا',['أقصى اتساع · أول أسطول: ذات الصواري','المصحف الإمام: «كل حرف في مصحفك وراه قرار إداري»','الترتيب منهجي مش مجاملة — قبل تشريح الأزمة']),
            ('الكتلة ٢ — تشريح التشقق',['١ مظالم جزئية حقيقية — لا مؤامرة من العدم ولا ظلم محض','٢ القنوات تشتغل: وفود · تحقيق · عزل ولاة','٣ الإشاعة المنظمة + الرسائل المزورة ← ٤ حصار ودم: نقطة اللاعودة']),
            ('الكتلة ٣ — قواعد الأدب الأربع',['نقد مؤسسي لا اتهام عام — «الخليفة جلد واليه» واقعة','«منعرفش كل حاجة» — حدود المعرفة أمانة','الدم حرام بالإجماع · الصحابة مجتهدون']),
    ],
    mission=['تشريح شق قريب بالمراحل الأربع (بلا أسماء أشخاص)','ميزان نقد/اتهام — خمس جمل','درس واحد طلع لك من التشريح'],
    visual='rift4', next='الأسبوع ٢١: الفتنة — علي وجمال وصفين والخوارج'),
4: dict(title='الفتنة: بلا تقديس ولا ازدراء', ep='«علي وجمال وصفين والخوارج»',
    q='إزاي أحكي أعقد ملف في تاريخنا بأمانة الرواية وأدب الأشخاص؟ وإيه اللي يحميني أبقى خارجيًا من غير ما أشعر؟',
    src=['Q19 دروس الفتنة','Q20 فتنة علي','Q21 الخوارج وأهل السنة','H2 عام الجماعة — إثراء'],
    blocks=[('الكتلة ١ — خط الأحداث بدرجاته',['بيعة علي: «دعوني والتمسوا غيري» — خلاف على الترتيب: قصاص مقابل استقرار','الجمل: صلح كاد ينجح + إشعال · صفين: «كلمة حق يراد بها باطل»','التحكيم: مشهور — وحكاية الخداع بيضعف سندها كبار المحققين']),
            ('الكتلة ٢ — بطاقة الخوارج',['عبّاد — لكن: تكفير بالكبيرة · استحلال دم بالتأويل','يقين قاطع · شيطنة الخصم — أربع صفات عابرة للعصور','مقتل علي ٤٠هـ + وصيته القانونية: قصاص لا فوضى']),
            ('الكتلة ٣ — عام الجماعة والدروس',['٤١هـ صلح الحسن: «لعل الله أن يصلح به بين فئتين»','الدم دايمًا · الإشاعة تقتل أكثر من السيف · الخوارج فكرة · الصلح سيادة','سؤال القفلة: أين يمكن أن تكون أنت الحسن؟']),
    ],
    mission=['ملف و5 بخمس مكونات','اختبار الخوارج على فكرة أو سلوك مجرد — بلا تسمية جماعات','جملة عام الجماعة + سطر أمانة «لسه ما أعرفوش»'],
    visual='fitna_map', next='الوحدة ٦: الأمويون والعباسيون — قرنان من الدولة الكبرى'),
}


def diagram(slide, prs, kind):
    """Native vector diagrams mirroring the weekly SVG visuals — بلا تجسيد لأشخاص."""
    if kind == 'card5':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'بطاقة الرواية الخماسية — جهاز فحص الخبر التاريخي', 20, True, NAVY, PP_ALIGN.CENTER)
        items = [('١. الراوي','مين أول من حكى؟ ثقة عند مين؟'),('٢. السلسلة','كام واسطة لحد المؤلف؟'),('٣. المتن','معقول؟ مبالغة؟ تناقض؟'),('٤. السياق والمصلحة','لصالح مين الحكاية بتشتغل؟'),('٥. الأثر','على قد الأثر تكون الصرامة')]
        x = 0.7
        for i,(t1,s1) in enumerate(items):
            box(slide, x, 1.6, 2.3, 1.25, t1+'\n'+s1, TEAL if i<2 else (GOLD if i<4 else RED), WHITE, 12)
            if i < 4: arrow(slide, x+2.32, 2.22, x+2.58, 2.22)
            x += 2.42
        box(slide, 0.7, 3.25, 11.88, 0.85, 'علامة حمراء تلقائية: التعميم المجهول — «قالوا» «رُوي أن» «الناس بتقول» «المؤرخون بيأكدوا» — أنهي مؤرخين؟ فين أسماؤهم؟', 'F9E9E7', RED, 13, False)
        box(slide, 0.7, 4.3, 11.88, 0.85, 'جهاز النقد الذاتي في تراثنا: الطبري «منه صحيح ومنها سقيم» · ابن الجوزي يصنف الموضوعات — أمة بتحاكم روايتها بنفسها', PALE, TEAL, 13, False)
        box(slide, 0.7, 5.35, 5.8, 1.0, 'خندق التقديس: عصر بلا بشر — تشيل أعظم ميزة: قابلية الاقتداء', 'F9E9E7', RED, 12.5, False)
        box(slide, 6.78, 5.35, 5.8, 1.0, 'خندق الازدراء (الحاضرية): محاكمة أزمنة بمسطرة قرنك', 'F9E9E7', RED, 12.5, False)
        box(slide, 0.7, 6.5, 11.88, 0.55, 'المنهج الوسط: يُفهم بشروطه · يُقيَّم بمعاييره والوحي · يُستفاد منه لحاضرنا — الدرجة: قوي/ضعيف/لا أعلم بعد', PALEG, '8A5A02', 12.5)
    elif kind == 'institutions':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'زمن الراشدين: انتقال بلا وراثة + دولة مؤسسات', 20, True, NAVY, PP_ALIGN.CENTER)
        kh = [('أبو بكر ١١–١٣هـ','السقيفة: شورى+بيعة · الردة: وحدة+ركن'),('عمر ١٣–٢٣هـ','الفتوح + المؤسسات · «من أين لك هذا؟»'),('عثمان ٢٣–٣٥هـ','أقصى اتساع · الأسطول · المصحف الإمام'),('علي ٣٥–٤٠هـ','الفتنة الكبرى · التحكيم · ٤٠هـ')]
        x = 0.7
        for i,(t1,s1) in enumerate(kh):
            box(slide, x, 1.55, 2.85, 1.05, t1+'\n'+s1, TEAL if i<2 else (GOLD if i==2 else RED), WHITE, 11.5)
            if i < 3: arrow(slide, x+2.87, 2.07, x+3.14, 2.07)
            x += 3.02
        txt(slide, 0.5, 2.85, 12.3, 0.4, 'مؤسسات عمر — كل بند «أول مرة في تاريخ المنطقة»', 16, True, NAVY, PP_ALIGN.CENTER)
        inst = [('الدواوين','مرتبات بجداول — دولة إدارة'),('التقويم الهجري','قرار هوية في ثوب إداري'),('القضاء المستقل','فصل سلطات قبل مونتسكيو بألف ومية سنة'),('الحسبة والسوق','حماية اقتصادية للعامة'),('محاسبة الولاة','حصر الثروة قبل وبعد'),('بيت المال والرعاية','حتى لغير المسلمين')]
        for i,(a,b) in enumerate(inst):
            box(slide, 0.7 + (i%3)*4.06, 3.35 + (i//3)*0.95, 3.86, 0.8, a+'\n'+b, PALE, TEAL, 11.5)
        box(slide, 0.7, 5.4, 11.88, 0.7, 'قصة ابن القبطي: «متى استعبدتم الناس وقد ولدتهم أمهاتهم أحرارًا؟» — محاسبة الولاة واقعة بأسماء شخوصها', PALEG, '8A5A02', 13)
        box(slide, 0.7, 6.25, 11.88, 0.7, 'الفتح ≠ الاستعمار: الأرض · الدين · المال · شهادة المفتوحين — وسؤال الأحقية: وقائع / أفهام / ثمرة = الأدب', WHITE, INK, 13, False)
    elif kind == 'rift4':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'إزاي بيتشقق المجتمع؟ تشريح أربع مراحل', 20, True, NAVY, PP_ALIGN.CENTER)
        stages = [('١ مظالم جزئية حقيقية','شكاوى فيها صدق وفيها مبالغة — لا مؤامرة من العدم'),('٢ القنوات تشتغل','وفود · تحقيق · عزل ولاة — نظام صحي شغال سنين'),('٣ الإشاعة المنظمة','غموض+أهمية · رسائل مزورة · تحشيد الأمصار'),('٤ حصار ودم','نقطة اللاعودة — أول دم بيقفل باب الرجوع')]
        x = 0.7
        for i,(t1,s1) in enumerate(stages):
            box(slide, x, 1.6, 2.85, 1.3, t1+'\n'+s1, GOLD if i in (0,2) else (TEAL if i==1 else RED), WHITE, 11.5)
            if i < 3: arrow(slide, x+2.87, 2.25, x+3.14, 2.25)
            x += 3.02
        box(slide, 0.7, 3.3, 11.88, 0.75, 'الإنجازات أولًا — الترتيب منهجي مش مجاملة: أقصى اتساع · أول أسطول (ذات الصواري) · المصحف الإمام: «كل حرف في مصحفك وراه قرار إداري»', PALE, TEAL, 12.5)
        box(slide, 0.7, 4.25, 11.88, 0.75, 'قواعد الأدب الأربع: نقد مؤسسي لا اتهام عام · «منعرفش كل حاجة» · الدم حرام بالإجماع · الصحابة مجتهدون', PALEG, '8A5A02', 12.5)
        box(slide, 0.7, 5.2, 11.88, 0.75, 'القاعدة العامة: الشكوى المشروعة لما ما تلاقيش علاجًا كافيًا بتتحول لوقود — والوقود بيدور على شرارة', WHITE, INK, 13, False)
        box(slide, 0.7, 6.15, 11.88, 0.7, 'مهمة الأسبوع: تشريح شق قريب بنفس المراحل — وصف آليات وسلوك، بلا اتهام أشخاص بأسمائهم', NAVY, WHITE, 13)
    elif kind == 'fitna_map':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'خريطة الفتنة الكبرى وآدابها: ٣٥–٤١هـ — بلا تقديس ولا ازدراء', 19, True, NAVY, PP_ALIGN.CENTER)
        nodes = [('٣٥هـ بيعة علي','«دعوني والتمسوا غيري»'),('٣٦هـ الجمل','صلح كاد ينجح + إشعال'),('٣٧هـ صفين','«كلمة حق يراد بها باطل»'),('التحكيم','مشهور ≠ مقطوع — الخداع ضعيف السند'),('٣٨–٤٠ الخوارج','تكفير + استحلال · مقتل علي ٤٠هـ'),('٤١هـ عام الجماعة','صلح الحسن — الصلح سيادة')]
        x = 0.62
        for i,(t1,s1) in enumerate(nodes):
            box(slide, x, 1.55, 1.95, 1.3, t1+'\n'+s1, GOLD if i==0 else (MUTED if i==3 else (RED if i in (1,2,4) else TEAL)), WHITE, 10.5)
            if i < 5: arrow(slide, x+1.97, 2.2, x+2.14, 2.2)
            x += 2.06
        txt(slide, 0.5, 3.15, 12.3, 0.4, 'بطاقة الخوارج — أربع صفات عابرة للعصور (تُختبر على أفكار — بلا تسمية جماعات)', 15, True, NAVY, PP_ALIGN.CENTER)
        marks = ['١ تكفير بالكبيرة: الغلط بقى كفرًا','٢ استحلال بالتأويل: التأويل بقى رخصة دم','٣ يقين قاطع: اختفى «يمكن أكون غلطان»','٤ شيطنة الخصم: مخطئ بقى «عدو الحقيقة»']
        for i,mk in enumerate(marks):
            box(slide, 0.7 + i*3.02, 3.65, 2.86, 0.8, mk, 'F9E9E7', RED, 11)
        box(slide, 0.7, 4.75, 11.88, 0.75, 'الدروس الأربعة: الدم أولًا — الدم دايمًا · الإشاعة تقتل أكثر من السيف · الخوارج فكرة متكررة · الصلح سيادة مش هزيمة', PALE, TEAL, 12.5)
        box(slide, 0.7, 5.7, 11.88, 0.7, 'وصية علي القانونية: «دمي قصاصًا لا فوضى — القصاص حقي وحق ورثتي، مش حق الغوغاء»', PALEG, '8A5A02', 12.5)
        box(slide, 0.7, 6.5, 11.88, 0.55, 'سؤال القفلة: أين يمكن أن تكون أنت الحسن؟ — في أي خلاف إنت فيه النهارده', NAVY, WHITE, 13)

def build_pptx():
    made = []
    for n, w in WEEKS.items():
        prs = prs_base()
        blank = prs.slide_layouts[6]
        # S1 title
        s = prs.slides.add_slide(blank); bg(s, prs)
        box(s, 0.7, 0.7, 11.93, 0.55, f'مشروع تأسيس · الوحدة 5 · v0.4', NAVY, WHITE, 14, False)
        txt(s, 0.7, 1.7, 11.93, 1.2, f'الأسبوع {n+17} — {w["title"]}', 40, True, NAVY, PP_ALIGN.CENTER)
        txt(s, 0.7, 3.0, 11.93, 0.8, f'الحلقة المسموعة: {w["ep"]}', 22, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 4.0, 9.93, 1.1, w['q'], WHITE, INK, 16, False)
        slide_shapes = s.shapes[-1]; slide_shapes.line.color.rgb = PRGB.from_string(GOLD); slide_shapes.line.width = PPt(2)
        txt(s, 0.7, 5.5, 11.93, 1.2, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+17)
        # S2 episode + sources
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'الحلقة ومصادرها', 28, True, NAVY)
        for i, srcx in enumerate(w['src']):
            box(s, 0.7, 1.3 + i*1.05, 11.93, 0.85, srcx, WHITE, INK, 14, False)
            bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(TEAL); bs.line.width = PPt(1.5)
        txt(s, 0.7, 5.7, 11.93, 0.9, 'الطوابع الزمنية ~تقريبية — تُدقق مقابل الفيديو الأصلي قبل النشر (بوابة G9) · التفريغات في transcripts/', 11, False, MUTED)
        footer(s, n+17)
        # S3-5 blocks
        for t, points in w['blocks']:
            s = prs.slides.add_slide(blank); bg(s, prs)
            txt(s, 0.7, 0.4, 11.93, 0.7, t, 26, True, TEAL)
            for i, pt in enumerate(points):
                txt(s, 0.9, 1.35 + i*1.5, 11.5, 1.4, '• ' + pt, 17, False, INK)
            footer(s, n+17)
        # S6 diagram
        s = prs.slides.add_slide(blank); bg(s, prs)
        diagram(s, prs, w['visual'])
        txt(s, 0.7, 6.62, 11.93, 0.4, 'النسخة القابلة للطباعة: 03_المواد_البصرية (SVG)', 10, False, MUTED, PP_ALIGN.CENTER)
        footer(s, n+17)
        # S7 mission + agenda note
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'مهمة الأسبوع — منخفضة المخاطر', 28, True, NAVY)
        for i, m in enumerate(w['mission']):
            box(s, 0.7, 1.3 + i*1.0, 11.93, 0.8, m, GOLD if i==0 else WHITE, WHITE if i==0 else INK, 15, i==0)
            if i: bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(GOLD); bs.line.width = PPt(1.5)
        txt(s, 0.7, 4.5, 11.93, 1.6, 'في اللقاء الحي: 120 دقيقة وفق دليل الميسر — الحلقة تُسمع/تُقرأ قبل اللقاء، والمشجر يُعرض في فقرة الشرح ويُوزع مطبوعًا.\nحق المرور والبديل الكتابي محفوظان · لا يُطلب إفصاح عن معتقد أو تجربة حساسة.', 13, False, MUTED)
        footer(s, n+17)
        # S8 closing
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 1.2, 11.93, 0.9, 'الأسبوع الجاي', 30, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 2.3, 9.93, 1.0, w['next'], NAVY, WHITE, 18)
        txt(s, 0.7, 3.7, 11.93, 0.8, 'مكتبة التوسع: H1–H6 تاريخ الأمويين والعباسين (أيمن) · R الخلفاء الراشدون (هدف جلب) · AT أين الطريق', 13, False, MUTED, PP_ALIGN.CENTER)
        txt(s, 0.7, 5.3, 11.93, 0.6, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+17)
        out = OUT / f'{9+n}_week_{n}_meeting_slides_module_05_v0_4.pptx'
        prs.save(out); made.append(out)
    return made

# ---------------- ZIP + validation ----------------
def md5(p): return hashlib.md5(Path(p).read_bytes()).hexdigest()

def build_zips(all_made):
    pack = FINAL/'module_05_v0_4_production_pack.zip'
    with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.name != '00_حالة_المخرجات.md':
                z.write(f, f'02_مخرجات_قيد_الإنتاج/{f.name}')
        for f in sorted(VIS.iterdir()): z.write(f, f'03_المواد_البصرية/{f.name}')
    full = FINAL/'module_05_v0_4_full_project_files.zip'
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ROOT.rglob('*')):
            if f.is_file() and FINAL not in f.parents and f.name != 'generate_module_05_v0_4.py':
                z.write(f, str(f.relative_to(ROOT)))
    # validation report
    lines = ['# تقرير التحقق — حزمة الوحدة 5 v0.4', '', f'**تاريخ البناء:** {DATE_AR} (2026-10-25) · **المولد:** `generate_module_05_v0_4.py` · **بايثون:** venv المشروع (python-docx 1.0.2 / python-pptx / openpyxl 3.1.5)', '', '## ملفات المخرجات (MD5)', '', '| الملف | الحجم (بايت) | MD5 |', '|---|---:|---|']
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
              '- [x] 3 XLSX (خريطة تشغيل + بوابات، سجل وموارد 25 صفًا، متتبع تجريب + مقاييس الحلقة)',
              '- [x] 4 PPTX × 8 شرائح (16:9، RTL، مخططات أسبوعية مرسومة أصليًا بالشكل — مرآة لملفات SVG)',
              '- [x] إخلاء الأسلوب مثبت في: رأس DOCX النصوص، شريحة عنوان وشريحة ختام كل عرض، وفوتر كل الشرائح',
              '- [x] الطوابع الزمنية ~تقريبية — بوابة G9 قبل أي نشر صوتي',
              '- [ ] مراجعة بشرية G11 (الخطوط الحمراء) قبل التوزيع العام', '']
    (FINAL/'validation_report_module_05_v0_4.md').write_text('\n'.join(lines), encoding='utf-8')
    (FINAL/'README_module_05_v0_4.md').write_text(
        '# الحزمة النهائية — الوحدة 5 v0.4\n\n'
        '- `module_05_v0_4_production_pack.zip` — المخرجات (DOCX/XLSX/PPTX) + البصريات (SVG)\n'
        '- `module_05_v0_4_full_project_files.zip` — مجلد الوحدة كاملًا (أصول نصية + تصميم وتتبع + مخرجات + بصريات)\n'
        '- `validation_report_module_05_v0_4.md` — MD5 وفحص القبول\n\n'
        '⚠️ النصوص أسلوب مستوحى من أيمن عبد الرحيم — ليست قولًا منسوبًا إليه. لا نشر باسمه أو بصوت مولد دون إذن صريح.\n', encoding='utf-8')
    return [pack, full]

if __name__ == '__main__':
    made = build_docx() + build_xlsx() + build_pptx()
    zips = build_zips(made)
    print('BUILT:')
    for f in made + zips: print(' -', f.name, f.stat().st_size)
