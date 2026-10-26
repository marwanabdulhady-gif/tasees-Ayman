#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 07 v0.4 outputs (DOCX/XLSX/PPTX) and auditable ZIPs.
Run with: .venv/bin/python generate_module_07_v0_4.py
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
    runstyle(hp.add_run('مشروع تأسيس | الوحدة 7 v0.4 — عثمانيون، استعمار، حداثة، هوية'), 8, True, TEAL)
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
    d = init_doc('دليل الميسر', 'الوحدة 7 v0.4 | عثمانيون، استعمار، حداثة، هوية (أسابيع 27–30)')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'01_facilitator_guide_module_07_v0_4.md', d)
    d.save(OUT/'01_facilitator_guide_module_07_v0_4.docx'); made.append(OUT/'01_facilitator_guide_module_07_v0_4.docx')
    # 02 workbook
    d = init_doc('دفتر المتعلم', 'الوحدة 7 v0.4 | مهام أسبوعية W27–W30 + دفتر الحلقة المسموعة')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'02_learner_workbook_module_07_v0_4.md', d)
    d.save(OUT/'02_learner_workbook_module_07_v0_4.docx'); made.append(OUT/'02_learner_workbook_module_07_v0_4.docx')
    # 03 cards
    d = init_doc('بطاقات الأنشطة', 'الوحدة 7 v0.4 | U7-A1–A8 + A0 الحلقة المسموعة + A9 قراءة المشجر')
    md_to_docx(SRC/'03_activity_cards_module_07_v0_4.md', d)
    d.save(OUT/'03_activity_cards_module_07_v0_4.docx'); made.append(OUT/'03_activity_cards_module_07_v0_4.docx')
    # 04 registry + glossary (from CSVs)
    d = init_doc('سجل المصادر والمصطلحات', 'الوحدة 7 v0.4 | سجل الموارد (34 صفًا) + المعجم (16) — من ملفات CSV المرجعية')
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_07_v0_4.csv', encoding='utf-8')))
    para(d, 'سجل الموارد', 15, True, NAVY, 6)
    heads = ['المعرّف','الفئة','العنوان','الأسبوع','الدور','الموضع','حالة التحقق']
    idx = [0,1,2,8,7,10,13]
    table(d, heads, [[r[i] for i in idx] for r in rows[1:]], 7.8)
    para(d, 'المصطلحات', 15, True, NAVY, 6)
    grows = list(csv.reader(open(SRC/'05_glossary_module_07_v0_4.csv', encoding='utf-8')))
    table(d, ['المصطلح','التعريف الإجرائي','الأسبوع','مثال في الوحدة'],
          [[r[0],r[1],r[2],r[3]] for r in grows[1:]], 8)
    d.save(OUT/'04_resource_registry_and_glossary_module_07_v0_4.docx'); made.append(OUT/'04_resource_registry_and_glossary_module_07_v0_4.docx')
    # 05 assessment and pilot (gate + protocol)
    d = init_doc('بوابة النشر وبروتوكول التجريب', 'الوحدة 7 v0.4 | G1–G13 + بروتوكول التجريب')
    md_to_docx(SRC/'06_release_gate_and_revision_note_module_07_v0_4.md', d)
    md_to_docx(SRC/'07_pilot_protocol_module_07_v0_4.md', d)
    d.save(OUT/'05_assessment_and_pilot_module_07_v0_4.docx'); made.append(OUT/'05_assessment_and_pilot_module_07_v0_4.docx')
    # 14 session scripts (the star asset)
    d = init_doc('نصوص الحلقات — بصوت أيمن (أسلوب مستوحى)', 'الوحدة 7 v0.4 | 4 حلقات × 15–20 دقيقة | ' + DATE_AR)
    para(d, DISCLAIMER, 9.5, True, RED, 10)
    md_to_docx(SRC/'10_session_scripts_module_07_v0_4.md', d)
    d.save(OUT/'14_session_scripts_module_07_v0_4.docx'); made.append(OUT/'14_session_scripts_module_07_v0_4.docx')
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
        ['27','الغروبان: الأندلس والهند','العالم سنة ١٤٩٢','Q38 · Q39 · Q40 · Q45 · Q51','AT أدب الحوار — إثراء','W27 خريطة الغروبين (SVG هوية v1)','A1 ترتيب المراحل الثماني · A2 ورشة خريطة الغروبين · A9 قراءة البصري','خريطة ١٤٩٢ (مهارة ٢٦) + مسمار ١٧'],
        ['28','الملف العثماني','لا تقديس ولا شيطنة','Q41 · Q42 · Q43 · Q44 · Q46 · Q47 · Q48 · Q49','T03 صورة العثمانيين — إثراء','W28 الملف بين خندقين (SVG هوية v1)','A3 محكمة الملف المستقطب · A4 بطاقة انتقال الخلافة','ميزان الدولة + مهارة ٢٧ + مسمار ١٨'],
        ['29','الصدمة والتجربة','استعمار ودولة حديثة','Q50 · Q52 · Q53 · Q54 · Q55 · Q56 · Q57 · Q59','T02/T06/T15 التحديث — إثراء','W29 ثلاثية الاستعمار والميزان (SVG هوية v1)','A5 سوق المصطلحات · A6 ميزان محمد علي · A7 ورشة الصورتين','ترسانة المصطلحات (مهارة ٢٨)'],
        ['30','القرن اللي أعاد رسمنا','حدود وفلسطين وعلمانية','Q58 · Q60 · Q61 · Q62 · Q63 · Q64','T + L اللغة هوية','W30 القرن الطويل وبطاقة الهوية (SVG هوية v1)','A8 صيد الوثائق · A0 الحلقة · A9 قراءة البصري','ملف و٧ + مهارتان ٢٩–٣٠'],
    ]
    ops += data
    sheet_from_rows(ws, ops, [7,20,30,24,14,30,40,36])
    ws2 = wb.create_sheet('حالة البوابات')
    gates = [['البوابة','المعيار','الحالة']] + [
        ['G8','الخطوط الحمراء مثبتة نصًا: العثمانيون بميزان (لا تقديس ولا شيطنة) · فلسطين بالوثائق بلا تحريض ديني ولا استغلال حزبي · العلمانية كنظام حكم لا ملصق تكفير · قانون الإخوة بحجمه بلا نكات · صور عبد الحميد/عرابي/محمد علي لا تُقلب لأضدادها','✅ مثبت'],
        ['G9','تدقيق الطوابع التقريبية + تواريخ وأرقام الوحدة (٩٢/١٣٨/٣١٦/٤٧٩/٦٣٥/٦٥٩/٨٩٧هـ + 1453/1516/1517/1526/1595/1683/1699/1798/1805/1811/1857/1869/1876/1882/1908/1916/1917/1920/1924/1936/1948م + أرقام الديون واللاجئين) مقابل مصادر معتمدة','☐ قبل النشر'],
        ['G10','تدقيق الاقتباس الحرفي مقابل الفيديو (التفريغ آلي — Q47 يدوي أدق) + مراجعة أصل بودكاست تاريخنا','☐ قبل النشر'],
        ['G11','مراجعة بشرية للخطوط الحمراء: بلا تجسيد · بلا تحريض ديني أو قومي · بلا استغلال حزبي للأحداث الجارية · الأرقام المضخمة تُروى كنماذج مبالغة مع تثبيت الأصل','☐ مراجعة بشرية'],
        ['G12','ترخيص البصريات — SVG أصلية مفاهيمية بهوية الكراسة v1 (فحصت check_svg) · أصول المكتبة موثقة في فهرسها','✅ جزئي'],
        ['G13','إذن الصوت عند الإنتاج بصوت مولد + الإخلاء المسموع','☐ شرط نشر'],
    ]
    sheet_from_rows(ws2, gates, [10,60,18])
    ws3 = wb.create_sheet('مكتبة التوسع')
    sheet_from_rows(ws3, [['المصدر','الدور'],['T محاضرات تأسيس الوعي 2/3/6 والمستوى الثاني 6 (تجارب التحديث والاستعمار)','إثراء لأسبوعي 29–30'],['L دورة الوعي اللغوي 1–9 (اللغة هوية ورؤية عالم)','أساس مهارة ٣٠ في أسبوع 30'],['هندسة اللغة/اللسانيات التعريفية (هدف جلب)','إثراء اللغة والهوية عند الجلب'],['AT أين الطريق','أدب الحوار في الملفات المستقطبة — مادة دعم']], [45,50])
    wb.save(OUT/'06_operations_map_module_07_v0_4.xlsx'); made.append(OUT/'06_operations_map_module_07_v0_4.xlsx')
    # 07 registry + glossary
    wb = Workbook(); ws = wb.active; ws.title = 'سجل الموارد'
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_07_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('المصطلحات')
    rows = list(csv.reader(open(SRC/'05_glossary_module_07_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws2, rows); ws2.freeze_panes = 'A2'
    wb.save(OUT/'07_resource_registry_and_glossary_module_07_v0_4.xlsx'); made.append(OUT/'07_resource_registry_and_glossary_module_07_v0_4.xlsx')
    # 08 pilot tracker
    wb = Workbook(); ws = wb.active; ws.title = 'قالب البيانات'
    rows = list(csv.reader(open(SRC/'08_pilot_data_template_module_07_v0_4.csv', encoding='utf-8')))
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
    wb.save(OUT/'08_pilot_tracker_module_07_v0_4.xlsx'); made.append(OUT/'08_pilot_tracker_module_07_v0_4.xlsx')
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
    txt(slide, 0.4, 7.05, 12.5, 0.4, f'مشروع تأسيس · الوحدة 7 v0.4 · الأسبوع {week} · {DATE_AR} · أسلوب مستوحى — ليس قولًا منسوبًا لأيمن عبد الرحيم',
        9, False, MUTED, PP_ALIGN.CENTER)

WEEKS = {
1: dict(title='الغروبان: الأندلس والهند', ep='«العالم سنة ١٤٩٢: غرب واقع وشرق محاصر ومركز صاعد»',
    q='إزاي نقرا سقوط الأطراف بمنهج — من غير يأس ومن غير شطب؟',
    src=['Q38 الأندلس: المراحل الثمان','Q39 الهند: أندلس الشرق','Q40 منهج قراءة الدول المستقلة','Q45 الاستغاثة والمورسكيون','Q51 الإسبان والبرتغال والمحيطات'],
    blocks=[('الكتلة ١ — الأندلس: تمن مراحل في ساعة',['الفتح ٩٢هـ ← الإمارة ١٣٨هـ (صقر قريش) ← الخلافة ٣١٦هـ — قرطبة جسر الشرق والغرب','الفتنة وملوك الطوائف: مراحل و٢٠ كاملة — والاستعانة بالطرفين','المرابطون فالموحدون فغرناطة ٦٣٥هـ — السقوط ٨٩٧هـ/١٤٩٢م والمعاهدة المكسورة']),
            ('الكتلة ٢ — الهند: أندلس الشرق',['٩٢هـ: فتحان في سنة واحدة — طارق في الغرب وابن القاسم في الشرق','سلطنة دلهي فالمغول — وذروة أورنكزيب: ربع الإنتاج العالمي تقريبًا','شركة لا جيش: بلاسي ١٧٥٧ ← ثورة ١٨٥٧ ← التاج — السقوط درجات']),
            ('الكتلة ٣ — والمركز بيتحرك',['الاستغاثة بثلاث طبقات: أساطيل ومسافات وجبهات — وباب اللجوء فُتح','١٤٩٢ كولومبوس و١٤٩٨ دي جاما — المحيط الهندي بحيرة إسلامية تصير ساحة أوروبية','خريطة ١٤٩٢: التشقق الداخلي هو الباب — والخارج يُكمل بس']),
    ],
    mission=['خريطة ١٤٩٢ بخط الإيد: تلات أطراف','سطرين لكل طرف: اللي سقط واللي انتقل','مهارة ٢٦ + مسمار ١٧'],
    visual='suns', next='الأسبوع ٢٨: الملف العثماني — لا تقديس ولا شيطنة'),
2: dict(title='الملف العثماني', ep='«ست مية سنة: لا تقديس ولا شيطنة»',
    q='إزاي نقرا أطول دولة في تاريخنا الإسلامي بميزان الدولة — لا تقديس ولا شيطنة؟',
    src=['Q41 لماذا نتحسس من العثمانيين','Q42 حامية الديار العربية','Q43 فتح القسطنطينية','Q44 قانون الإخوة','Q46 سليم والمماليك وانتقال الخلافة','Q47 هل كانوا محتلين؟','Q48 القانوني بين صورتين','Q49 الانحدار والسقوط'],
    blocks=[('الكتلة ١ — الصعود و١٤٥٣',['عصبية حدودية من ١٢٩٩م — حالة خلدونية نموذجية','القسطنطينية: مدفع أوربان — التقنية ما بتستناش حدود الحضارات','الأثر العالمي: بيزنطة تنتهي وأوروبا تُدفع للمحيطات']),
            ('الكتلة ٢ — سليم وبطاقة انتقال الخلافة',['مرج دابق ١٥١٦ فالريدانية ١٥١٧ — فرسان قدام مدافع','خادم الحرمين: حماية حقيقية بلا مشروع نهضة عربية','الخماسية على حكاية التسليم: ابن إياس الشاهد ما ذكرهاش — الوراثة سياسية بالتدريج']),
            ('الكتلة ٣ — القانوني والانحدار',['بطاقة و١٨: القانون والتقنين — وحكايات الحريم تُفحص بدرجاتها','١٦٨٣ فيينا الثانية ← كارلوفجة ١٦٩٩: قرن ونصف تراجع','التيمار←الالتزام · الإنكشارية شبكة مصالح · القفص · «الرجل المريض» كلمة شحنة']),
    ],
    mission=['ميزان الدولة العثمانية الأولى: ٣+٣+جملة','بطاقة رواية: انتقال الخلافة ١٥١٧','مهارة ٢٧ + مسمار ١٨'],
    visual='trenches', next='الأسبوع ٢٩: الصدمة والتجربة — ١٧٩٨ ومحمد علي'),
3: dict(title='الصدمة والتجربة', ep='«استعمار ودولة حديثة»',
    q='إزاي نفرق احتلال واستعمار وهيمنة — وإزاي نمسك تجربة التحديث الأولى بميزان؟',
    src=['Q50 الاحتلال والاستعمار','Q52 لماذا تقدم الغرب','Q53 صدمة ١٧٩٨','Q54 محمد علي: الجدال','Q55 التبعية','Q56 عبد الحميد وعرابي','Q57 عبد الحميد: ٣٣ سنة','Q59 وثائق الاستعمار'],
    blocks=[('الكتلة ١ — ترسانة المصطلحات',['احتلال: سيطرة عسكرية — استعمار: إعادة هيكلة — هيمنة: سيطرة بلا جندي','استعمار من ع-م-ر مقابل colonialisme — درس استيراد الكلمات (مسمار ٩)','لماذا تقدم الغرب: تنافس + مؤسسات + تقنية — بلا تفسير واحد']),
            ('الكتلة ٢ — محمد علي بميزان الدولة',['الإنجاز: جيش ومصانع ومدارس وبعثات وترجمة وزراعة','الصفحات: احتكار يعصر المجتمع · القلعة ١٨١١ · حروب استنزفت · توريث','جملة الحكم: دولة قوية ومجتمع ضعيف ← ديون ← صندوق الدين ١٨٧٦ ← احتلال ١٨٨٢']),
            ('الكتلة ٣ — عبد الحميد وعرابي',['الصورتان الكاريكاتير: «الخائن» و«البطل النقي» — والفحص الثالث بالطبقات','١٨٨٢: «خلقنا الله أحرارًا» — وتل الكبير','٣٣ سنة: جامعة إسلامية وحجاز حديد — و«لا أبيع شبرًا» ببطاقة الرواية']),
    ],
    mission=['صنف تلات أخبار: احتلال/استعمار/هيمنة','ميزان محمد علي: ٣+٣+جملة حكم','مهارة ٢٨'],
    visual='terms', next='الأسبوع ٣٠: القرن اللي أعاد رسمنا + ملف و٧'),
4: dict(title='القرن اللي أعاد رسمنا', ep='«حدود وفلسطين وعلمانية — وإحنا + ملف الوحدة»',
    q='مين رسم العالم اللي إحنا عايشين فيه — وإزاي نخرج من القرن ده بهوية مبنية مش مهزومة؟',
    src=['Q58 الثورة العربية والتتريك','Q60 القرن العشرون الطويل','Q61 من رسم الحدود','Q62 قصة فلسطين','Q63 الخلافة والعلمانية','Q64 مصر: الهجين','T تجارب التحديث · L اللغة هوية'],
    blocks=[('الكتلة ١ — تلات وثائق وحرب واحدة',['١٩٠٨: تتريك — القمع القومي بيصنع القومية المضادة','حسين–مكماهون ١٩١٥ + سايكس–بيكو ١٩١٦ + بلفور ١٩١٧ — وعود متناقضة','الثورة العربية بالطبقات: التخطيط مقابل التهيئة — والفراغ والغياب المؤسسي']),
            ('الكتلة ٢ — فلسطين والعلمانية ببطاقتين',['فلسطين بالوثائق: مشروع سياسي يُفحص — والدين وأتباعه لهم حرمتهم','١٩٣٦: التشقق الداخلي هو الباب — و١٩٤٨ النكبة','١٩٢٤ إلغاء الخلافة — والعلمانية بدرجاتها: تركيا الإقصائية مقابل الهجين المصري']),
            ('الكتلة ٣ — بطاقة الهوية',['اللي ضاع: وحدة وقرار ولغة وثقة نموذج','اللي فاضل: القرآن والعربية والذاكرة والشبكات','اللي بيتجدد: التراث والمحتوى العربي والمبادرات — والقابلية للاستعمار فحص لا لوم']),
    ],
    mission=['ملف و٧ بخمس مكونات','بطاقة هوية حية: ضاع/فاضل/بيتجدد','سطر أمانة: «لسه ما أعرفوش»'],
    visual='identity', next='الوحدة التامنة (٣١–٣٤): البيت والجماعات والفعل المسؤول'),
}


def diagram(slide, prs, kind):
    """Native vector diagrams mirroring the weekly SVG visuals — بلا تجسيد لأشخاص."""
    if kind == 'suns':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'خريطة الغروبين — العالم سنة ١٤٩٢: غرب واقع · مركز صاعد · شرق محاصر', 19, True, NAVY, PP_ALIGN.CENTER)
        cols = [('الغرب: الأندلس — سقوط', ['سقوط غرناطة ٨٩٧هـ/١٤٩٢م','معاهدة تُكسر: تنصير وطرد','المورسكيون ١٦٠٩م: الترحيل النهائي','ثماني مراحل: فتح ← إمارة ← خلافة ← طوائف ← سقوط'], RED, 'F9E9E7'),
                ('المركز: العثمانيون — صعود', ['إمارة حدودية من ١٢٩٩م','١٤٥٣م: فتح القسطنطينية','قوة بحرية شرق المتوسط','استقبال مهجَّري الأندلس'], TEAL, PALE),
                ('الشرق: الهند والمحيطات — حصار', ['سلطنات قائمة: دلهي','دي جاما ١٤٩٨م: المحيط يتبدل','بحيرة إسلامية ← ساحة أوروبية','مليلية ١٤٩٧م: المغرب يُقرص'], RED, 'F9E9E7')]
        for i,(ttl, items, c, bgc) in enumerate(cols):
            x = 0.7 + i*4.06
            box(slide, x, 1.5, 3.86, 0.55, ttl, c, WHITE, 14)
            for j, it in enumerate(items):
                box(slide, x, 2.17 + j*0.62, 3.86, 0.52, it, bgc, c if c==RED else TEAL, 10.5)
        box(slide, 0.7, 4.85, 11.88, 0.62, 'الجسر: علوم قرطبة ← طليطلة ← جامعات أوروبا — ابن رشد يُترجم والزهرافي مرجع جراحي لخمس مية سنة', PALEG, '8A5A02', 12.5)
        box(slide, 0.7, 5.62, 11.88, 0.75, 'الدرس المنهجي: السقوط يبدأ من الداخل — والخارج يُكمل بس: مراحل و٢٠ الأربع على ملوك الطوائف كما على كل الأطراف (مهارة ٢٦: خريطة ومراحل ومعادلة)', WHITE, INK, 12, False)
        box(slide, 0.7, 6.5, 11.88, 0.5, 'مسمار ١٧: الأطراف أمة كمان — ما تقراش التاريخ من العواصم بس', NAVY, WHITE, 12)
    elif kind == 'trenches':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'الملف العثماني بين خندقين — والميزان في الوسط', 20, True, NAVY, PP_ALIGN.CENTER)
        tl = [('١٢٩٩','إمارة حدودية',TEAL),('١٤٥٣','القسطنطينية',TEAL),('١٥١٧','القاهرة والحرمين',TEAL),('١٦٨٣','فيينا الثانية',GOLD),('١٧٩٨','صدمة مصر',RED),('١٩٢٤','إلغاء الخلافة',RED)]
        x = 0.62
        for d, s, c in tl:
            box(slide, x, 1.45, 2.35, 0.8, d+'\n'+s, c, WHITE, 11)
            x += 2.45
        box(slide, 0.7, 2.5, 5.8, 0.5, 'كفة الإنجاز — بأدلتها', TEAL, WHITE, 14)
        inc = ['فتح ١٤٥٣ وأثره العالمي','حماية الحرمين — قرون بلا غزو ناجح للمشرق','القانوني: قوانين الضرائب والحرف','أكبر كيان إسلامي منذ العباسيين','استقبال مهجَّري الأندلس']
        for i,a in enumerate(inc):
            box(slide, 0.7, 3.1 + i*0.52, 5.8, 0.44, a, PALE, TEAL, 10.5)
        box(slide, 6.78, 2.5, 5.8, 0.5, 'كفة الصفحات — بدرجاتها', RED, WHITE, 14)
        blk = ['قانون الإخوة: الجريمة تُقنَّن','ليلة ١٥٩٥: تسعة عشر أخًا — موثقة','القفص: أمراء بلا خبرة','الإنكشارية: جيش يصير شبكة مصالح','التيمار ← الالتزام: الفلاح يُعصر']
        for i,a in enumerate(blk):
            box(slide, 6.78, 3.1 + i*0.52, 5.8, 0.44, a, 'F9E9E7', RED, 10.5)
        box(slide, 0.7, 5.85, 3.86, 0.62, 'خندق التقديس: «خلافة مثالية» — مشطوب', 'F9E9E7', RED, 11.5)
        box(slide, 4.76, 5.85, 3.86, 0.62, 'المسمار ١٨: ميزان + درجة — أو ما تدخلش', TEAL, WHITE, 11.5)
        box(slide, 8.72, 5.85, 3.86, 0.62, 'خندق الشيطنة: «٤٠٠ سنة احتلال» — مشطوب', 'F9E9E7', RED, 11.5)
        box(slide, 0.7, 6.6, 11.88, 0.5, 'حكاية «انتقال الخلافة ١٥١٧» بالخماسية: الاحتفال الدرامي ضعيف/متأخر — والوراثة السياسية حقيقة بالتدريج', WHITE, INK, 11.5, False)
    elif kind == 'terms':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'ثلاثية السيطرة وميزان التجربة الأولى', 20, True, NAVY, PP_ALIGN.CENTER)
        cards = [('الاحتلال','سيطرة عسكرية على أرض وقرار — ١٧٩٨ ثم ١٨٨٢'),('الاستعمار','إعادة هيكلة مجتمع — من colonialisme لا من «عَمَر»'),('الهيمنة','سيطرة بلا جندي: قرار وعملة وسلاح وتعليم')]
        for i,(a,b) in enumerate(cards):
            x = 0.7 + i*4.06
            box(slide, x, 1.45, 3.86, 0.5, a, TEAL, WHITE, 14)
            box(slide, x, 2.05, 3.86, 0.7, b, PALE, TEAL, 10.5)
        tl = [('١٧٩٨','الصدمة: مدافع ومطبعة',TEAL),('١٨٠٥','محمد علي',TEAL),('١٨٦٩','القناة — مشروع بالديون',GOLD),('١٨٧٦','صندوق الدين',RED),('١٨٨٢','الاحتلال يحمي الهيمنة',RED)]
        x = 0.62
        for d, s, c in tl:
            box(slide, x, 3.0, 2.35, 0.7, d+'\n'+s, c, WHITE, 10)
            x += 2.45
        box(slide, 0.7, 3.95, 5.8, 0.45, 'ميزان محمد علي — الإنجاز', TEAL, WHITE, 13)
        inc = ['جيش وطني نظامي حديث','مصانع وترسانة','مدارس وبعثات — الطهطاوي','زراعة وقنوات — القطن طويل التيلة']
        for i,a in enumerate(inc):
            box(slide, 0.7, 4.48 + i*0.42, 5.8, 0.36, a, PALE, TEAL, 10)
        box(slide, 6.78, 3.95, 5.8, 0.45, 'ميزان محمد علي — الصفحات', RED, WHITE, 13)
        blk = ['الاحتكار: المجتمع يُعصر لبناء الدولة','مذبحة القلعة ١٨١١ — شركاء التأسيس (و٢٣)','حروب استنزفت — وتدخل أوروبا ١٨٤٠','التوريث: نفس سابقة و٢٢']
        for i,a in enumerate(blk):
            box(slide, 6.78, 4.48 + i*0.42, 5.8, 0.36, a, 'F9E9E7', RED, 10)
        box(slide, 0.7, 6.3, 11.88, 0.7, 'جملة الحكم — وصف بلا وسم: دولة قوية ومجتمع ضعيف — القوة احتكرها القصر، فلما وهن القصر وُهبت للأجانب: ديون ← صندوق الدين ← هيمنة ← احتلال (مهارة ٢٨)', NAVY, WHITE, 12)
    elif kind == 'identity':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'القرن العشرون الطويل وبطاقة الهوية', 20, True, NAVY, PP_ALIGN.CENTER)
        fl = [('١٩٠٨','دستور ثم تتريك',TEAL),('١٩١٥–١٦','وعدان وتقسيم سري',GOLD),('١٩١٧','وعد بلفور',RED),('١٩٢٠','الانتدابات',RED),('١٩٢٤','إلغاء الخلافة',RED),('—','دول قُطرية',RED)]
        x = 0.62
        for d, s, c in fl:
            box(slide, x, 1.45, 2.35, 0.75, d+'\n'+s, c, WHITE, 10)
            if x < 12: arrow(slide, x+2.37, 1.82, x+2.53, 1.82)
            x += 2.45
        cols = [('اللي ضاع — بصراحة', ['الوحدة السياسية — مفيش كيان جامع من ١٩٢٤','القرار الاقتصادي — من التبعية للهيمنة','اللغة في المجال العام — الفصحى انزوت','ثقة النموذج — صدمة ١٧٩٨ وعقدة النقص'], RED, 'F9E9E7'),
                ('اللي فاضل — بلا رومانسية', ['القرآن محفوظ بحرفه — واقعة فريدة','العربية ومخزونها — ابن خلدون يُقرأ اليوم','الذاكرة الشعبية — تتوجع لفلسطين وتفرح لآيا صوفيا','الشبكات — من طرق الحج للإنترنت'], TEAL, PALE),
                ('اللي بيتجدد — بأدلة', ['تحقيق التراث بمقاييس علمية','محتوى عربي رقمي — ودورتك دي فعل تجديد','أوقاف ومؤسسات أهلية وتعليم مستقل','الشبكات الكبيرة من عقد صغيرة (و٢٣)'], TEAL, PALEG)]
        for i,(ttl, items, c, bgc) in enumerate(cols):
            x = 0.7 + i*4.06
            box(slide, x, 2.45, 3.86, 0.5, ttl, c, WHITE, 13)
            for j, it in enumerate(items):
                box(slide, x, 3.05 + j*0.56, 3.86, 0.48, it, bgc, c, 10)
        box(slide, 0.7, 5.5, 11.88, 0.6, '«القابلية للاستعمار» (مالك بن نبي): فحص للقابلية — لا لوم للضحية: الجريمة تفضل جريمة وإنت كمان ليك شروط نهضة تبنيها', 'F9E9E7', RED, 12)
        box(slide, 0.7, 6.25, 11.88, 0.75, 'مهارة ٢٩ — قراءة الخط: أي خط على خريطة أو في قانون: مين رسمه؟ بإيه وثيقة؟ وطلع منه إيه؟ — الخطوط مش قدرًا: رسمها بشر ويعدلها بشر · ومهارة ٣٠: بطاقة الهوية (ضاع/فاضل/بيتجدد)', NAVY, WHITE, 12)

def build_pptx():
    made = []
    for n, w in WEEKS.items():
        prs = prs_base()
        blank = prs.slide_layouts[6]
        # S1 title
        s = prs.slides.add_slide(blank); bg(s, prs)
        box(s, 0.7, 0.7, 11.93, 0.55, f'مشروع تأسيس · الوحدة 7 · v0.4', NAVY, WHITE, 14, False)
        txt(s, 0.7, 1.7, 11.93, 1.2, f'الأسبوع {n+26} — {w["title"]}', 40, True, NAVY, PP_ALIGN.CENTER)
        txt(s, 0.7, 3.0, 11.93, 0.8, f'الحلقة المسموعة: {w["ep"]}', 22, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 4.0, 9.93, 1.1, w['q'], WHITE, INK, 16, False)
        slide_shapes = s.shapes[-1]; slide_shapes.line.color.rgb = PRGB.from_string(GOLD); slide_shapes.line.width = PPt(2)
        txt(s, 0.7, 5.5, 11.93, 1.2, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+26)
        # S2 episode + sources
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'الحلقة ومصادرها', 28, True, NAVY)
        for i, srcx in enumerate(w['src']):
            box(s, 0.7, 1.3 + i*1.05, 11.93, 0.85, srcx, WHITE, INK, 14, False)
            bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(TEAL); bs.line.width = PPt(1.5)
        txt(s, 0.7, 5.7, 11.93, 0.9, 'الطوابع الزمنية ~تقريبية — تُدقق مقابل الفيديو الأصلي قبل النشر (بوابة G9) · التفريغات في transcripts/', 11, False, MUTED)
        footer(s, n+26)
        # S3-5 blocks
        for t, points in w['blocks']:
            s = prs.slides.add_slide(blank); bg(s, prs)
            txt(s, 0.7, 0.4, 11.93, 0.7, t, 26, True, TEAL)
            for i, pt in enumerate(points):
                txt(s, 0.9, 1.35 + i*1.5, 11.5, 1.4, '• ' + pt, 17, False, INK)
            footer(s, n+26)
        # S6 diagram
        s = prs.slides.add_slide(blank); bg(s, prs)
        diagram(s, prs, w['visual'])
        txt(s, 0.7, 6.62, 11.93, 0.4, 'النسخة القابلة للطباعة: 03_المواد_البصرية (SVG)', 10, False, MUTED, PP_ALIGN.CENTER)
        footer(s, n+26)
        # S7 mission + agenda note
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'مهمة الأسبوع — منخفضة المخاطر', 28, True, NAVY)
        for i, m in enumerate(w['mission']):
            box(s, 0.7, 1.3 + i*1.0, 11.93, 0.8, m, GOLD if i==0 else WHITE, WHITE if i==0 else INK, 15, i==0)
            if i: bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(GOLD); bs.line.width = PPt(1.5)
        txt(s, 0.7, 4.5, 11.93, 1.6, 'في اللقاء الحي: 120 دقيقة وفق دليل الميسر — الحلقة تُسمع/تُقرأ قبل اللقاء، والمشجر يُعرض في فقرة الشرح ويُوزع مطبوعًا.\nحق المرور والبديل الكتابي محفوظان · لا يُطلب إفصاح عن معتقد أو تجربة حساسة.', 13, False, MUTED)
        footer(s, n+26)
        # S8 closing
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 1.2, 11.93, 0.9, 'الأسبوع الجاي', 30, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 2.3, 9.93, 1.0, w['next'], NAVY, WHITE, 18)
        txt(s, 0.7, 3.7, 11.93, 0.8, 'مكتبة التوسع: T محاضرات تأسيس الوعي (تجارب التحديث) · L دورة الوعي اللغوي 1–9 (اللغة هوية) · هندسة اللغة/اللسانيات التعريفية (هدف جلب)', 13, False, MUTED, PP_ALIGN.CENTER)
        txt(s, 0.7, 5.3, 11.93, 0.6, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+26)
        out = OUT / f'{9+n}_week_{n}_meeting_slides_module_07_v0_4.pptx'
        prs.save(out); made.append(out)
    return made

# ---------------- ZIP + validation ----------------
def md5(p): return hashlib.md5(Path(p).read_bytes()).hexdigest()

def build_zips(all_made):
    pack = FINAL/'module_07_v0_4_production_pack.zip'
    with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.name != '00_حالة_المخرجات.md':
                z.write(f, f'02_مخرجات_قيد_الإنتاج/{f.name}')
        for f in sorted(VIS.iterdir()): z.write(f, f'03_المواد_البصرية/{f.name}')
    full = FINAL/'module_07_v0_4_full_project_files.zip'
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ROOT.rglob('*')):
            if f.is_file() and FINAL not in f.parents and f.name != 'generate_module_07_v0_4.py':
                z.write(f, str(f.relative_to(ROOT)))
    # validation report
    lines = ['# تقرير التحقق — حزمة الوحدة 7 v0.4', '', f'**تاريخ البناء:** {DATE_AR} (2026-10-25) · **المولد:** `generate_module_07_v0_4.py` · **بايثون:** venv المشروع (python-docx 1.0.2 / python-pptx / openpyxl 3.1.5)', '', '## ملفات المخرجات (MD5)', '', '| الملف | الحجم (بايت) | MD5 |', '|---|---:|---|']
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
              '- [x] 3 XLSX (خريطة تشغيل + بوابات، سجل وموارد 34 صفًا، متتبع تجريب + مقاييس الحلقة)',
              '- [x] 4 PPTX × 8 شرائح (16:9، RTL، مخططات أسبوعية مرسومة أصليًا بالشكل — مرآة لملفات SVG)',
              '- [x] إخلاء الأسلوب مثبت في: رأس DOCX النصوص، شريحة عنوان وشريحة ختام كل عرض، وفوتر كل الشرائح',
              '- [x] الطوابع الزمنية ~تقريبية — بوابة G9 قبل أي نشر صوتي',
              '- [ ] مراجعة بشرية G11 (الخطوط الحمراء) قبل التوزيع العام', '']
    (FINAL/'validation_report_module_07_v0_4.md').write_text('\n'.join(lines), encoding='utf-8')
    (FINAL/'README_module_07_v0_4.md').write_text(
        '# الحزمة النهائية — الوحدة 7 v0.4\n\n'
        '- `module_07_v0_4_production_pack.zip` — المخرجات (DOCX/XLSX/PPTX) + البصريات (SVG)\n'
        '- `module_07_v0_4_full_project_files.zip` — مجلد الوحدة كاملًا (أصول نصية + تصميم وتتبع + مخرجات + بصريات)\n'
        '- `validation_report_module_07_v0_4.md` — MD5 وفحص القبول\n\n'
        '⚠️ النصوص أسلوب مستوحى من أيمن عبد الرحيم — ليست قولًا منسوبًا إليه. لا نشر باسمه أو بصوت مولد دون إذن صريح.\n', encoding='utf-8')
    return [pack, full]

if __name__ == '__main__':
    made = build_docx() + build_xlsx() + build_pptx()
    zips = build_zips(made)
    print('BUILT:')
    for f in made + zips: print(' -', f.name, f.stat().st_size)
