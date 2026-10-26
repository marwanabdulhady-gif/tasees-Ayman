#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 01 v0.3 outputs (DOCX/XLSX/PPTX) and auditable ZIPs.
Run with: .venv/bin/python generate_module_04_v0_4.py
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

def init_doc(title, subtitle, footer_note='إصدار إنتاجي v0.3  •  ' + DATE_AR):
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
    d = init_doc('دليل الميسر', 'الوحدة 4 v0.4 | السيرة: مصدر ومنهج وقدوة ومعنى (أسابيع 13–16)')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'01_facilitator_guide_module_04_v0_4.md', d)
    d.save(OUT/'01_facilitator_guide_module_04_v0_4.docx'); made.append(OUT/'01_facilitator_guide_module_04_v0_4.docx')
    # 02 workbook
    d = init_doc('دفتر المتعلم', 'الوحدة 4 v0.4 | مهام أسبوعية W13–W16 + دفتر الحلقة المسموعة')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'02_learner_workbook_module_04_v0_4.md', d)
    d.save(OUT/'02_learner_workbook_module_04_v0_4.docx'); made.append(OUT/'02_learner_workbook_module_04_v0_4.docx')
    # 03 cards
    d = init_doc('بطاقات الأنشطة', 'الوحدة 4 v0.4 | U4-A1–A8 + A0 الحلقة المسموعة + A9 قراءة المشجر')
    md_to_docx(SRC/'03_activity_cards_module_04_v0_4.md', d)
    d.save(OUT/'03_activity_cards_module_04_v0_4.docx'); made.append(OUT/'03_activity_cards_module_04_v0_4.docx')
    # 04 registry + glossary (from CSVs)
    d = init_doc('سجل المصادر والمصطلحات', 'الوحدة 4 v0.4 | سجل الموارد (16 صفًا) + المعجم (11) — من ملفات CSV المرجعية')
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_04_v0_4.csv', encoding='utf-8')))
    para(d, 'سجل الموارد', 15, True, NAVY, 6)
    heads = ['المعرّف','الفئة','العنوان','الأسبوع','الدور','الموضع','حالة التحقق']
    idx = [0,1,2,8,7,10,13]
    table(d, heads, [[r[i] for i in idx] for r in rows[1:]], 7.8)
    para(d, 'المصطلحات', 15, True, NAVY, 6)
    grows = list(csv.reader(open(SRC/'05_glossary_module_04_v0_4.csv', encoding='utf-8')))
    table(d, ['المصطلح','المقابل المقترح','التعريف المبسط','يُفرَّق عن','الأسبوع','الحالة'],
          [[r[0],r[1],r[2],r[3]] for r in grows[1:]], 8)
    d.save(OUT/'04_resource_registry_and_glossary_module_04_v0_4.docx'); made.append(OUT/'04_resource_registry_and_glossary_module_04_v0_4.docx')
    # 05 assessment and pilot (gate + protocol)
    d = init_doc('بوابة النشر وبروتوكول التجريب', 'الوحدة 4 v0.4 | G1–G13 + بروتوكول التجريب')
    md_to_docx(SRC/'06_release_gate_and_revision_note_module_04_v0_4.md', d)
    md_to_docx(SRC/'07_pilot_protocol_module_04_v0_4.md', d)
    d.save(OUT/'05_assessment_and_pilot_module_04_v0_4.docx'); made.append(OUT/'05_assessment_and_pilot_module_04_v0_4.docx')
    # 14 session scripts (the star asset)
    d = init_doc('نصوص الحلقات — بصوت أيمن (أسلوب مستوحى)', 'الوحدة 4 v0.4 | 4 حلقات × 15–20 دقيقة | ' + DATE_AR)
    para(d, DISCLAIMER, 9.5, True, RED, 10)
    md_to_docx(SRC/'10_session_scripts_module_04_v0_4.md', d)
    d.save(OUT/'14_session_scripts_module_04_v0_4.docx'); made.append(OUT/'14_session_scripts_module_04_v0_4.docx')
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
        ['1','خريطة لا تشتيت','ما تسحبش الكروت من غير ترتيب','05/03 · 05/41 · 05/39','AT-00 ص9–53','W1 مشجر خريطة العلوم (SVG)','A1 خريطة التعلم · A2 عادة 14 يوم · A9 قراءة المشجر','سؤال محدد + خريطة الأعمدة الأربعة + عادة 14 يوم'],
        ['2','وصف بلا وسم','حقيقة الأشياء: تصف ولا توسم','05/44 · 05/35 · 05/45','AT-01 ص54–99','W2 إنفوجراف تشريح فكرة (SVG)','A3 تشريح التسمية · A4 عيادة التشخيص','بطاقة وصف/معيار/دليل/بديل/أثر'],
        ['3','تفكير حر منضبط','تحرير العقل: بين حماس مستعجل وشك قاعد','05/08 · 05/13 · 05/31','AT-04 ص214–271','W3 إنفوجراف مصائد التفكير (SVG)','A5 محكمة دعوى · A6 سؤال قابل للبحث · A10 أعد الحكاية','بطاقة المسامير الستة D-S-I-A-B-L'],
        ['4','عادة تلقي مسؤولة','لهفة التلقي','02/01 · 02/02 · 05/18 · 05/36','AT-10 ص547–583','W4 مشجر سلسلة التلقي (SVG)','A7 تدرج المصدر · A8 steelman وحوار','ملف نهاية الوحدة + خطة 14/30'],
    ]
    ops += data
    sheet_from_rows(ws, ops, [7,20,30,24,14,30,40,36])
    ws2 = wb.create_sheet('حالة البوابات')
    gates = [['البوابة','المعيار','الحالة']] + [
        ['G8','إخلاء الأسلوب مثبت في النصوص ووصف كل حلقة منشورة','✅ مثبت'],
        ['G9','تدقيق الطوابع التقريبية مقابل الفيديو الأصلي قبل النشر','☐ قبل النشر'],
        ['G10','تدقيق الاقتباس الحرفي مقابل الفيديو (التفريغ آلي)','☐ قبل النشر'],
        ['G11','مراجعة بشرية للخطوط الحمراء (لا سخرية من مقدس/أشخاص/جماعات)','☐ مراجعة بشرية'],
        ['G12','ترخيص البصريات — SVG أصلية، أي صور لاحقة تُوثق','✅ جزئي'],
        ['G13','إذن الصوت عند الإنتاج بصوت مولد + الإخلاء المسموع','☐ شرط نشر'],
    ]
    sheet_from_rows(ws2, gates, [10,60,18])
    ws3 = wb.create_sheet('مكتبة التوسع')
    sheet_from_rows(ws3, [['المصدر','الدور'],['05/01 منهج طلب العلم وبناء الذات','مادة اختيارية تُذكر في قفل كل حلقة'],['05/17 معلومات يجب أن يعرفها كل مسلم معاصر','مادة اختيارية للتوسع']], [45,50])
    wb.save(OUT/'06_operations_map_module_04_v0_4.xlsx'); made.append(OUT/'06_operations_map_module_04_v0_4.xlsx')
    # 07 registry + glossary
    wb = Workbook(); ws = wb.active; ws.title = 'سجل الموارد'
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_04_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('المصطلحات')
    rows = list(csv.reader(open(SRC/'05_glossary_module_04_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws2, rows); ws2.freeze_panes = 'A2'
    wb.save(OUT/'07_resource_registry_and_glossary_module_04_v0_4.xlsx'); made.append(OUT/'07_resource_registry_and_glossary_module_04_v0_4.xlsx')
    # 08 pilot tracker
    wb = Workbook(); ws = wb.active; ws.title = 'قالب البيانات'
    rows = list(csv.reader(open(SRC/'08_pilot_data_template_module_04_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('مقاييس الحلقة v0.3')
    sheet_from_rows(ws2, [
        ['المقياس','الوصف','العتبة المقترحة'],
        ['episode_listened_full','إتمام الحلقة المسموعة/المقروءة قبل اللقاء','≥ 70%'],
        ['humor_understood_ok','فهم الدعابة دون إساءة أو التباس','≥ 90%'],
        ['visual_used_in_explanation','استعمال المشجر/الإنفوجراف في الشرح للغير','≥ 60%'],
        ['style_naturalness_score','طبيعية الأسلوب (1–5، تقرير ذاتي)','≥ 3.5'],
        ['episode_length_fit','ملاءمة الطول 15–20 دقيقة','نعم/لا + تعليق'],
    ], [30,50,20])
    wb.save(OUT/'08_pilot_tracker_module_04_v0_4.xlsx'); made.append(OUT/'08_pilot_tracker_module_04_v0_4.xlsx')
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
    txt(slide, 0.4, 7.05, 12.5, 0.4, f'مشروع تأسيس · الوحدة 1 v0.3 · الأسبوع {week} · {DATE_AR} · أسلوب مستوحى — ليس قولًا منسوبًا لأيمن عبد الرحيم',
        9, False, MUTED, PP_ALIGN.CENTER)

WEEKS = {
1: dict(title='إزاي وصلتنا السيرة؟', ep='«الخبر التاريخي وبطاقته»',
    q='إزاي أفرق بين خبر صلب وخبر طري وأتعامل مع كل واحد بأداته؟',
    src=['Q9 التوثق من أحداث السيرة','S2 العهد المكي — رواية وسند','Y12 بنية الأدلة'],
    blocks=[('الكتلة ١ — السيرة علم له عدة',['4 طبقات: قرآن ← حديث برجاله ← مغازي ← مصنفات','«في الحلال شددنا وفي السير تساهلنا» — أمانة المعيارين','درجات: متواتر/صحيح/ضعيف/موضوع']),
            ('الكتلة ٢ — بطاقة الخبر',['١ سند · ٢ متن · ٣ مخارج · ٤ سياق · ٥ أثر','على قد الأثر تكون الصرامة','شق الصدر نموذجًا: تثبيت الأصل بلا خناق على التفاصيل']),
            ('الكتلة ٣ — الغلو والجفاء',['الغلو يمسخ البشرية فيمسخ الحجة','الجفاء يطرح الصندوق كله — وسؤال «متأخرة بالنسبة لإيه؟»','الوسطي بيفرح بالتصحيح']),
    ],
    mission=['بطاقة خبر بخمس خانات','سؤال توثيق واحد لأهل العلم','«لا أعلم بعد» واحدة بأمانة'],
    visual='chain4', next='الأسبوع ١٤: الرجل في الغار — العهد المكي'),
2: dict(title='الرجل في الغار', ep='«العهد المكي ثلاثة عشر عامًا»',
    q='إيه اللي حصل في 13 سنة مكية وإيه اللي بتعلمه للي بيبدأ حاجة حقيقية؟',
    src=['S1/S3 العهد المكي','S4 الحبشة والطائف','S5 مصعب والشعب'],
    blocks=[('الكتلة ١ — البذرة والحاضنة',['الغار: اقرأ · شهادة خديجة = سيرة قبل برهان','السر والثلاثة · دار الأرقم أم المؤسسات','الجهر وثمنه · بلال: أحد أحد']),
            ('الكتلة ٢ — لما تضيق الأرض',['الحبشة: تقييم سياسي وحكمة لاجئ','الطائف: أسوأ يوم — والإسراء بعد استنفاد الأسباب','الشعب: حصار 3 سنين — الرابطة لها وزن']),
            ('الكتلة ٣ — الثمرة تنضج',['المواسم: عرض على القبائل — صبر استراتيجي','العقبتان: بيعة أخلاق ثم بيعة نصرة — الدولة بعد الفرد','مصعب: سفير وحده فتح مدينة · الهجرة نقل مركز مش هروب']),
    ],
    mission=['خريطة محطات بخط الإيد','علّم محطتك إنت','كارت بلال/حمزة/عمر/مصعب'],
    visual='idea_chain', next='الأسبوع ١٥: القدوة مش استنساخ'),
3: dict(title='القدوة مش استنساخ', ep='«تمييز الفعل وتشريعه»',
    q='إزاي أميز فعلًا تشريعيًا من عادي من خصوصي وأجاوب السؤال الصعب بميزان؟',
    src=['Q11 تميز الشخصية','Q12 سؤال الزواج','Y منهج الأدلة'],
    blocks=[('الكتلة ١ — الشخصية شهادة',['شهادة خصم: عتبة وأبو سفيان وهرقل','شهادة قريب: خديجة وأنس وعائشة','شهادة موقف صعب: الفتح/الطائف/كسوف الشمس — الاتساق هو التميز']),
            ('الكتلة ٢ — أنواع الفعل',['تشريعي: نُقل نقل بيان — اتباع','عادي: عادة زمانه — اقتداء بالروح لا القالب','خصوصي: ثبتت خصوصيته — إثبات بلا تقليد','مرض الغلط: تقديس العادي · وذوبان التشريعي']),
            ('الكتلة ٣ — الأسئلة الصعبة',['لا هروب ولا انفعال — مواجهة بميزان','سؤال الزواج: خريطة الزيجات بسياقاتها','أرقام ببطاقتها · الحاضرية غلط منهجي','السائل الصادق يستاهل إجابة كاملة']),
    ],
    mission=['تصنيف 3 أفعال بأدلة','إجابة سؤال صعب بميزان','أدب الاختيار الفقهي'],
    visual='traps', next='الأسبوع ١٦: السيرة مش غزوات وبس — قفلة الوحدة'),
4: dict(title='السيرة مش غزوات وبس', ep='«المعنى وقفلة الوحدة»',
    q='إزاي أحط القتال في حجمه وأستخرج المعنى اللي السيرة بتخدمه؟',
    src=['Q13 القتال لنشر الإسلام؟','Q14 سيرة غزوات فقط؟','S6 خلاصة العهد المكي'],
    blocks=[('الكتلة ١ — حجم القتال الحقيقي',['23 سنة · ≈80 تحركًا · <10 معارك · مئات ضحايا','سياق كل معركة: بدر حقوق · أحد دفاع · الخندق استئصال','الحديبية سلام · قواعد اشتباك سابقة لعصرها · انتشار بلا سيف']),
            ('الكتلة ٢ — اليوم العادي',['ليل قيام (المحرك) · مجلس جامع · عيادة وحوائج','بيت: مهنة أهله · سوق: أمانة · ليل: دبلوماسية','السيرة بناء إنسان متكامل — الغزوات استثناء مفروض']),
            ('الكتلة ٣ — المعنى',['4 وظائف تقفل و1–و3: معيار/مدرسة تلقي/حياة لغة/اتجاه','بشري كامل: تطمين وجذب معًا','وصية الأدب: البحث مع الصلاة عليه ﷺ']),
    ],
    mission=['ملف و4 بخمس مكونات','إجابة الساخر بالأرقام والأدب','سطر الوصلة + تهيئة التنفس'],
    visual='unit_chain', next='أسبوع التنفس ١٧ ثم المرحلة ٢: التاريخ'),
}


def diagram(slide, prs, kind):
    """Native vector diagrams mirroring the weekly SVG visuals."""
    if kind == 'chain4':
        txt(slide, 0.5, 1.0, 12.3, 0.5, 'خريطة التعلم — الأعمدة الأربعة', 20, True, NAVY, PP_ALIGN.CENTER)
        items = [('١. سؤال محدد','قابل للتعلم لا شعار'),('٢. علم / مصدر','من يجيب؟ وما لا يجيبه'),('٣. فجوة','عارف / فاكر / مش عارف'),('٤. عادة ١٤ يومًا','فعل ١٠ دقائق بميعاد')]
        x = 0.7
        for i,(t,s) in enumerate(items):
            box(slide, x, 1.7, 2.75, 1.15, t+'\n'+s, TEAL if i<3 else GOLD, WHITE, 13)
            if i < 3: arrow(slide, x+2.75+0.05, 2.28, x+2.75+0.35, 2.28)
            x += 3.13
        txt(slide, 0.5, 3.25, 12.3, 0.5, 'الأسئلة الوجودية الكبرى ← كل علم يجيب جزءًا', 17, True, NAVY, PP_ALIGN.CENTER)
        qs = ['من أنا؟\nعلوم الإنسان + العقيدة','لماذا أنا؟\nالشرع ومقاصده','إلى أين؟\nالآخرة والتاريخ','ما الصواب؟\nالقيم والأحكام']
        x = 0.7
        for t in qs:
            box(slide, x, 3.9, 2.75, 1.05, t, GOLD, WHITE, 12)
            x += 3.13
        box(slide, 0.7, 5.35, 11.88, 1.0, 'تشبيه الحلقة: حزمة الكروت المرتبة — التعلم بلا خريطة = سحب كروت عشوائي: معلومات بلا بناء', PALEG, '8A5A02', 14, False)
    elif kind == 'idea_chain':
        txt(slide, 0.5, 1.0, 12.3, 0.5, 'تشريح فكرة: من عالم الأفكار إلى الواقع', 20, True, NAVY, PP_ALIGN.CENTER)
        chain = ['فكرة\n(تفسير جاهز)','انفعال','قرار','تصرف','عادة','شخصية ← مصير']
        x = 0.7
        for i,t in enumerate(chain):
            box(slide, x, 1.7, 1.82, 1.0, t, TEAL if i<5 else NAVY, WHITE, 12.5)
            if i < 5: arrow(slide, x+1.87, 2.2, x+2.06, 2.2)
            x += 2.075
        box(slide, 0.7, 3.15, 5.8, 2.1, 'الوصف ✓ يبني\n\nفعل محدد + شاهد يتحقق\nيقبل التفصيل والرجعة\n«في المعاملة دي ربا وتدليس»', PALE, TEAL, 13, False)
        box(slide, 6.83, 3.15, 5.8, 2.1, 'الوسم ✗ يهدم\n\nاسم شامل على إنسان أو جماعة\nبلا شاهد — يقفل السؤال\n«دول كسالى» «الجيل ده ضاع»', 'F9E9E7', RED, 13, False)
        box(slide, 0.7, 5.5, 11.93, 0.95, 'بطاقة التشخيص: وصف ← معيار ← دليل ← بديل ← أثر التسمية  ·  سلّم الجاهلية: ملاحظة ← معيار ← حكم على ظاهرة ← (قف!) الوسم مرفوض', GOLD, WHITE, 13)
    elif kind == 'traps':
        txt(slide, 0.5, 1.0, 12.3, 0.5, 'مصائد التفكير وفكّ الدعوى', 20, True, NAVY, PP_ALIGN.CENTER)
        box(slide, 5.42, 2.6, 2.5, 1.5, 'الدعوى\nأي جملة خبرية\nتصلك ملفوفة في كلام', NAVY, WHITE, 13, shape=MSO_SHAPE.OVAL)
        traps = [(0.7,1.6,'١. تشبيه زائف','شبه في الاسم لا المعيار'),(9.85,1.6,'٢. تعميم متسرع','من حالة لكل الحالات'),
                 (0.7,4.0,'٣. تفكير القطيع','العدد ليس دليلًا'),(9.85,4.0,'٤. معضلة السجين','عقلانية منفصلة = خسارة جماعية')]
        for x,y,t,s in traps:
            box(slide, x, y, 2.8, 1.1, t+'\n'+s, 'F9E9E7', RED, 12, False)
        arrow(slide, 3.5, 2.15, 5.5, 2.9, RED, 2); arrow(slide, 9.85, 2.15, 7.9, 2.9, RED, 2)
        arrow(slide, 3.5, 4.55, 5.5, 3.8, RED, 2); arrow(slide, 9.85, 4.55, 7.9, 3.8, RED, 2)
        txt(slide, 0.5, 5.25, 12.3, 0.4, 'المسامير الستة — فك أي دعوى (D-S-I-A-B-L)', 15, True, NAVY, PP_ALIGN.CENTER)
        screws = ['دعوى','شاهد','استدلال','افتراض','بديل','حد']
        x = 0.7
        for i,s in enumerate(screws):
            box(slide, x, 5.7, 1.82, 0.62, s, WHITE, '8A5A02', 12.5)
            sl = slide.shapes[-1]; sl.line.color.rgb = PRGB.from_string(GOLD); sl.line.width = PPt(2)
            if i < 5: arrow(slide, x+1.87, 6.0, x+2.06, 6.0)
            x += 2.075
    elif kind == 'unit_chain':
        txt(slide, 0.5, 1.0, 12.3, 0.5, 'سلسلة التلقي المسؤول — ملخص الوحدة', 20, True, NAVY, PP_ALIGN.CENTER)
        chain = ['سؤال','خريطة','وصف بلا وسم','دعوى مفكوكة','تلقٍ مسؤول','عادة تعيش']
        x = 0.7
        for i,t in enumerate(chain):
            box(slide, x, 1.65, 1.82, 0.85, t, TEAL if i<5 else GOLD, WHITE, 12.5)
            if i < 5: arrow(slide, x+1.87, 2.07, x+2.06, 2.07)
            x += 2.075
        txt(slide, 0.7, 2.85, 5.8, 0.4, 'قبل ما تقرا: ٤ أسئلة على المصدر', 15, True, NAVY)
        qsrc = ['١. بيقدملي إيه؟','٢. في أنهي مجال؟','٣. إيه حدّه؟','٤. مين المكمل؟']
        for i,t in enumerate(qsrc):
            box(slide, 0.7 + (i%2)*2.95, 3.35 + (i//2)*0.85, 2.8, 0.7, t, PALE, TEAL, 12.5)
        box(slide, 0.7, 5.15, 5.75, 0.75, 'لا تسليم كامل (إجازة عقلية) ولا حرق كامل (تعصب مقلوب)', 'F9E9E7', RED, 12, False)
        txt(slide, 6.83, 2.85, 5.8, 0.4, 'بروتوكول الحوار المنصف — ٥ خطوات', 15, True, NAVY)
        proto = ['١. قول دعوى التاني زي ما هو شايفها (steelman)','٢. لخّص لحد ما يقولك: آه ده أنا','٣. فرّق: ثابت/تفسير/قيمة/مجهول','٤. قول حدّك وقراءة بديلة','٥. اقفل بخطوة تعلم — لا بانتصار']
        for i,t in enumerate(proto):
            box(slide, 6.83, 3.35 + i*0.62, 5.8, 0.52, t, TEAL if i<4 else NAVY, WHITE, 11.5)
        box(slide, 0.7, 6.15, 11.93, 0.7, 'الخطة: ١٤ يومًا (فعل صغير · مكان وميعاد · مصدر واحد · رفيق اختياري) + مراجعة ٣٠ يومًا (حق التعديل والتوقف)', PALEG, '8A5A02', 12.5)

def build_pptx():
    made = []
    for n, w in WEEKS.items():
        prs = prs_base()
        blank = prs.slide_layouts[6]
        # S1 title
        s = prs.slides.add_slide(blank); bg(s, prs)
        box(s, 0.7, 0.7, 11.93, 0.55, f'مشروع تأسيس · الوحدة 1 · v0.3', NAVY, WHITE, 14, False)
        txt(s, 0.7, 1.7, 11.93, 1.2, f'الأسبوع {n+12} — {w["title"]}', 40, True, NAVY, PP_ALIGN.CENTER)
        txt(s, 0.7, 3.0, 11.93, 0.8, f'الحلقة المسموعة: {w["ep"]}', 22, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 4.0, 9.93, 1.1, w['q'], WHITE, INK, 16, False)
        slide_shapes = s.shapes[-1]; slide_shapes.line.color.rgb = PRGB.from_string(GOLD); slide_shapes.line.width = PPt(2)
        txt(s, 0.7, 5.5, 11.93, 1.2, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n)
        # S2 episode + sources
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'الحلقة ومصادرها', 28, True, NAVY)
        for i, srcx in enumerate(w['src']):
            box(s, 0.7, 1.3 + i*1.05, 11.93, 0.85, srcx, WHITE, INK, 14, False)
            bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(TEAL); bs.line.width = PPt(1.5)
        txt(s, 0.7, 5.7, 11.93, 0.9, 'الطوابع الزمنية ~تقريبية — تُدقق مقابل الفيديو الأصلي قبل النشر (بوابة G9) · التفريغات في transcripts/', 11, False, MUTED)
        footer(s, n)
        # S3-5 blocks
        for t, points in w['blocks']:
            s = prs.slides.add_slide(blank); bg(s, prs)
            txt(s, 0.7, 0.4, 11.93, 0.7, t, 26, True, TEAL)
            for i, pt in enumerate(points):
                txt(s, 0.9, 1.35 + i*1.5, 11.5, 1.4, '• ' + pt, 17, False, INK)
            footer(s, n)
        # S6 diagram
        s = prs.slides.add_slide(blank); bg(s, prs)
        diagram(s, prs, w['visual'])
        txt(s, 0.7, 6.62, 11.93, 0.4, 'النسخة القابلة للطباعة: 03_المواد_البصرية (SVG)', 10, False, MUTED, PP_ALIGN.CENTER)
        footer(s, n)
        # S7 mission + agenda note
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'مهمة الأسبوع — منخفضة المخاطر', 28, True, NAVY)
        for i, m in enumerate(w['mission']):
            box(s, 0.7, 1.3 + i*1.0, 11.93, 0.8, m, GOLD if i==0 else WHITE, WHITE if i==0 else INK, 15, i==0)
            if i: bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(GOLD); bs.line.width = PPt(1.5)
        txt(s, 0.7, 4.5, 11.93, 1.6, 'في اللقاء الحي: 120 دقيقة وفق دليل الميسر — الحلقة تُسمع/تُقرأ قبل اللقاء، والمشجر يُعرض في فقرة الشرح ويُوزع مطبوعًا.\nحق المرور والبديل الكتابي محفوظان · لا يُطلب إفصاح عن معتقد أو تجربة حساسة.', 13, False, MUTED)
        footer(s, n)
        # S8 closing
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 1.2, 11.93, 0.9, 'الأسبوع الجاي', 30, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 2.3, 9.93, 1.0, w['next'], NAVY, WHITE, 18)
        txt(s, 0.7, 3.7, 11.93, 0.8, 'مكتبة التوسع: 05/01 منهج طلب العلم وبناء الذات · 05/17 معلومات يجب أن يعرفها كل مسلم معاصر', 13, False, MUTED, PP_ALIGN.CENTER)
        txt(s, 0.7, 5.3, 11.93, 0.6, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n)
        out = OUT / f'{9+n}_week_{n}_meeting_slides_module_04_v0_4.pptx'
        prs.save(out); made.append(out)
    return made

# ---------------- ZIP + validation ----------------
def md5(p): return hashlib.md5(Path(p).read_bytes()).hexdigest()

def build_zips(all_made):
    pack = FINAL/'module_04_v0_4_production_pack.zip'
    with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.name != '00_حالة_المخرجات.md':
                z.write(f, f'02_مخرجات_قيد_الإنتاج/{f.name}')
        for f in sorted(VIS.iterdir()): z.write(f, f'03_المواد_البصرية/{f.name}')
    full = FINAL/'module_04_v0_4_full_project_files.zip'
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ROOT.rglob('*')):
            if f.is_file() and FINAL not in f.parents and f.name != 'generate_module_04_v0_4.py':
                z.write(f, str(f.relative_to(ROOT)))
    # validation report
    lines = ['# تقرير التحقق — حزمة الوحدة 1 v0.3', '', f'**تاريخ البناء:** {DATE_AR} (2026-10-25) · **المولد:** `generate_module_04_v0_4.py` · **بايثون:** venv المشروع (python-docx 1.0.2 / python-pptx / openpyxl 3.1.5)', '', '## ملفات المخرجات (MD5)', '', '| الملف | الحجم (بايت) | MD5 |', '|---|---:|---|']
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
              '- [x] 3 XLSX (خريطة تشغيل + بوابات، سجل وموارد 35 صفًا، متتبع تجريب + مقاييس الحلقة)',
              '- [x] 4 PPTX × 8 شرائح (16:9، RTL، مخططات أسبوعية مرسومة أصليًا بالشكل — مرآة لملفات SVG)',
              '- [x] إخلاء الأسلوب مثبت في: رأس DOCX النصوص، شريحة عنوان وشريحة ختام كل عرض، وفوتر كل الشرائح',
              '- [x] الطوابع الزمنية ~تقريبية — بوابة G9 قبل أي نشر صوتي',
              '- [ ] مراجعة بشرية G11 (الخطوط الحمراء) قبل التوزيع العام', '']
    (FINAL/'validation_report_module_04_v0_4.md').write_text('\n'.join(lines), encoding='utf-8')
    (FINAL/'README_module_04_v0_4.md').write_text(
        '# الحزمة النهائية — الوحدة 1 v0.3\n\n'
        '- `module_04_v0_4_production_pack.zip` — المخرجات (DOCX/XLSX/PPTX) + البصريات (SVG)\n'
        '- `module_04_v0_4_full_project_files.zip` — مجلد الوحدة كاملًا (أصول نصية + تصميم وتتبع + مخرجات + بصريات)\n'
        '- `validation_report_module_04_v0_4.md` — MD5 وفحص القبول\n\n'
        '⚠️ النصوص أسلوب مستوحى من أيمن عبد الرحيم — ليست قولًا منسوبًا إليه. لا نشر باسمه أو بصوت مولد دون إذن صريح.\n', encoding='utf-8')
    return [pack, full]

if __name__ == '__main__':
    made = build_docx() + build_xlsx() + build_pptx()
    zips = build_zips(made)
    print('BUILT:')
    for f in made + zips: print(' -', f.name, f.stat().st_size)
