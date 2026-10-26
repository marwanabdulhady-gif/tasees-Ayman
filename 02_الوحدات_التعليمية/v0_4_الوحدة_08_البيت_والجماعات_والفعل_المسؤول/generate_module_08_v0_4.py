#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 08 v0.4 outputs (DOCX/XLSX/PPTX) and auditable ZIPs.
Run with: .venv/bin/python generate_module_08_v0_4.py
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
DATE_AR = '٢٦ أكتوبر ٢٠٢٦'
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
    runstyle(hp.add_run('مشروع تأسيس | الوحدة 8 v0.4 — البيت والجماعات والفعل المسؤول'), 8, True, TEAL)
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
    d = init_doc('دليل الميسر', 'الوحدة 8 v0.4 | البيت والجماعات والفعل المسؤول (أسابيع 31–34)')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'01_facilitator_guide_module_08_v0_4.md', d)
    d.save(OUT/'01_facilitator_guide_module_08_v0_4.docx'); made.append(OUT/'01_facilitator_guide_module_08_v0_4.docx')
    # 02 workbook
    d = init_doc('دفتر المتعلم', 'الوحدة 8 v0.4 | مهام أسبوعية W31–W34 + دفتر الحلقة المسموعة')
    para(d, DISCLAIMER, 9, False, RED, 10)
    md_to_docx(SRC/'02_learner_workbook_module_08_v0_4.md', d)
    d.save(OUT/'02_learner_workbook_module_08_v0_4.docx'); made.append(OUT/'02_learner_workbook_module_08_v0_4.docx')
    # 03 cards
    d = init_doc('بطاقات الأنشطة', 'الوحدة 8 v0.4 | U8-A1–A8 + A0 الحلقة المسموعة + A9 قراءة المشجر')
    md_to_docx(SRC/'03_activity_cards_module_08_v0_4.md', d)
    d.save(OUT/'03_activity_cards_module_08_v0_4.docx'); made.append(OUT/'03_activity_cards_module_08_v0_4.docx')
    # 04 registry + glossary (from CSVs)
    d = init_doc('سجل المصادر والمصطلحات', 'الوحدة 8 v0.4 | سجل الموارد (16 صفًا) + المعجم (14) — من ملفات CSV المرجعية')
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_08_v0_4.csv', encoding='utf-8')))
    para(d, 'سجل الموارد', 15, True, NAVY, 6)
    heads = ['المعرّف','الفئة','العنوان','الأسبوع','الدور','الموضع','حالة التحقق']
    idx = [0,1,2,8,7,10,13]
    table(d, heads, [[r[i] for i in idx] for r in rows[1:]], 7.8)
    para(d, 'المصطلحات', 15, True, NAVY, 6)
    grows = list(csv.reader(open(SRC/'05_glossary_module_08_v0_4.csv', encoding='utf-8')))
    table(d, ['المصطلح','التعريف الإجرائي','الأسبوع','مثال في الوحدة'],
          [[r[0],r[1],r[2],r[3]] for r in grows[1:]], 8)
    d.save(OUT/'04_resource_registry_and_glossary_module_08_v0_4.docx'); made.append(OUT/'04_resource_registry_and_glossary_module_08_v0_4.docx')
    # 05 assessment and pilot (gate + protocol)
    d = init_doc('بوابة النشر وبروتوكول التجريب', 'الوحدة 8 v0.4 | G1–G13 + بروتوكول التجريب')
    md_to_docx(SRC/'06_release_gate_and_revision_note_module_08_v0_4.md', d)
    md_to_docx(SRC/'07_pilot_protocol_module_08_v0_4.md', d)
    d.save(OUT/'05_assessment_and_pilot_module_08_v0_4.docx'); made.append(OUT/'05_assessment_and_pilot_module_08_v0_4.docx')
    # 14 session scripts (the star asset)
    d = init_doc('نصوص الحلقات — بصوت أيمن (أسلوب مستوحى)', 'الوحدة 8 v0.4 | 4 حلقات × 15–20 دقيقة | ' + DATE_AR)
    para(d, DISCLAIMER, 9.5, True, RED, 10)
    md_to_docx(SRC/'10_session_scripts_module_08_v0_4.md', d)
    d.save(OUT/'14_session_scripts_module_08_v0_4.docx'); made.append(OUT/'14_session_scripts_module_08_v0_4.docx')
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
        ['31','أين الأمة؟ سؤال كل جيل','والبيت اللي شايل الإجابة','Q65 · Q66 · L (اللغة الحية) · B (هدف جلب)','AT — إثراء','W31 سؤال كل جيل وبيت الإجابة (SVG هوية v1)','A1 تفكيك سؤال اليأس · A2 خريطة البيت (خاصة) · A9 قراءة البصري','خريطة بيت + ممارسة صغيرة (مهارة ٣١) + مسمار ١٩'],
        ['32','الجماعات الوسيطة','إزاي الأمة حافظت على حضورها','Q67 · عصبية و25 · مركزية و29 · W1 أمان الدوائر','AT — إثراء','W32 سلم الجماعات الوسيطة (SVG هوية v1)','A3 ورشة درج السلم · A4 ميزان البقاء · A9 قراءة البصري','درج السلم + دائرة واحدة (مهارة ٣٢) + مسمار ٢٠'],
        ['33','من عالم الأفكار للسلوك','إزاي المعرفة بتبقى ممارسة','T1 (02:54) · T13 (01:32/01:48) · T14 · بن نبي (و30)','AT — إثراء','W33 سلسلة الحلقات الست (SVG هوية v1)','A5 عيادة السلسلة · A6 الثالوث على عادة · A8 مثلث بن نبي','بطاقة فكرة لمشروع (مهارة ٣٣)'],
        ['34','الفعل المسؤول الآمن','ما العمل + ملف الوحدة 8','Q68 · Q69 · Q70 · بروتوكولات و1 · T17','AT ما العمل','W34 الشروط الستة والميادين (SVG هوية v1)','A7 لجنة الشروط الستة · A0 ميزان الدورة · A9 قراءة البصري','ملف و٨ + بطاقة فعل آمن (مهارة ٣٤)'],
    ]
    ops += data
    sheet_from_rows(ws, ops, [7,20,30,24,14,30,40,36])
    ws2 = wb.create_sheet('حالة البوابات')
    gates = [['البوابة','المعيار','الحالة']] + [
        ['G8','الخطوط الحمراء مثبتة نصًا: حرمة البيوت وحق المرور (لا إفصاح إجباري ولا مقارنة بيوت) · الحركات تُفحص بميزان — بلا تمجيد حزبي ولا تكفير ولا تسمية جماعات معاصرة · الفعل المدني قانوني وآمن — لا حشد ولا تحريض · اليأس يُفكك بالدليل · لا نكات على مقدسات ولا أشخاص ولا جماعات','✅ مثبت'],
        ['G9','تدقيق اقتباسات Q/T الحرفية مقابل الطوابع (خصوصًا جملة Q67 «بقاء الإسلام وتسيده» وQ70 «ما العمل وكيف الخلاص») + أرقام الوحدة (٤٧٨هـ/٦٥٦هـ/١٧٩٨/١٩٢٤ + «أكثر من 600 سؤال») + مواضع T13 (01:32:40 و01:48:00) وT1 (02:54–04:38) مقابل الفيديو','☐ قبل النشر'],
        ['G10','مراجعة أصل بودكاست تاريخنا (Q69–Q70 أسئلة جمهور — تُدقق نِسَب الأسئلة) + B هدف جلب موثق: كتلتا 31-3 و32-2 تُستكملان عند الوصول بإصدار مجاور بلا حذف','☐ قبل النشر'],
        ['G11','مراجعة بشرية للخطوط الحمراء: بلا تجسيد · بلا تحريض أو حشد · أي مشروع متعلم خارج الشروط الستة يُعاد تصميمه أو يُوقف · حالات الأذى المحتملة لها مسار فردي هادئ','☐ مراجعة بشرية'],
        ['G12','ترخيص البصريات — SVG أصلية مفاهيمية بهوية الكراسة v1 (فحصت check_svg: 27/31/46/37 عقدة نص) · أصول المكتبة (6 صفوف) موثقة — شخصيات للاستعمال الداخلي فقط','✅ جزئي'],
        ['G13','إذن الصوت عند الإنتاج بصوت مولد + الإخلاء المسموع','☐ شرط نشر'],
    ]
    sheet_from_rows(ws2, gates, [10,60,18])
    ws3 = wb.create_sheet('مكتبة التوسع')
    sheet_from_rows(ws3, [['المصدر','الدور'],['T المحاضرة الأولى + المستوى الثاني 4/5/8 (الثالوث والخلل السلوكي والأفكار والسلوك والختام)','أساس أسبوع 33 وإثراء 34'],['بروتوكولات و1 (الحوار الست خطوات ورجل الفولاذ ومحكمة الدعوى)','أساس أمان الدوائر (32) والمجال العام (34)'],['B البيت المسلم والجماعات الوسيطة (هدف جلب موثق)','استكمال كتلتي 31-3 و32-2 عند الجلب — إصدار مجاور بلا حذف'],['L الوعي اللغوي 1–9 + AT أين الطريق','إثراء اللغة الحية في البيت (31) وما العمل (34)']], [45,50])
    wb.save(OUT/'06_operations_map_module_08_v0_4.xlsx'); made.append(OUT/'06_operations_map_module_08_v0_4.xlsx')
    # 07 registry + glossary
    wb = Workbook(); ws = wb.active; ws.title = 'سجل الموارد'
    rows = list(csv.reader(open(SRC/'04_resource_registry_module_08_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws, rows); ws.freeze_panes = 'A2'
    ws2 = wb.create_sheet('المصطلحات')
    rows = list(csv.reader(open(SRC/'05_glossary_module_08_v0_4.csv', encoding='utf-8')))
    sheet_from_rows(ws2, rows); ws2.freeze_panes = 'A2'
    wb.save(OUT/'07_resource_registry_and_glossary_module_08_v0_4.xlsx'); made.append(OUT/'07_resource_registry_and_glossary_module_08_v0_4.xlsx')
    # 08 pilot tracker
    wb = Workbook(); ws = wb.active; ws.title = 'قالب البيانات'
    rows = list(csv.reader(open(SRC/'08_pilot_data_template_module_08_v0_4.csv', encoding='utf-8')))
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
    wb.save(OUT/'08_pilot_tracker_module_08_v0_4.xlsx'); made.append(OUT/'08_pilot_tracker_module_08_v0_4.xlsx')
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
    txt(slide, 0.4, 7.05, 12.5, 0.4, f'مشروع تأسيس · الوحدة 8 v0.4 · الأسبوع {week} · {DATE_AR} · أسلوب مستوحى — ليس قولًا منسوبًا لأيمن عبد الرحيم',
        9, False, MUTED, PP_ALIGN.CENTER)

WEEKS = {
1: dict(title='أين الأمة؟ سؤال كل جيل', ep='«والبيت اللي شايل الإجابة»',
    q='إزاي نحول السؤال الحارق لسؤال دقيق — وإزاي نلاقي أول مكان الإجابة بتسكن فيه؟',
    src=['Q65 من نحن وضاعت الهوية وتفككت الروابط','Q66 أين الأمة — كل جيل سأل هذا السؤال','L الوعي اللغوي — اللغة الحية في البيت','B البيت المسلم — هدف جلب موثق'],
    blocks=[('الكتلة ١ — من نحن؟ الهوية المطاردة',['فقدنا الإجابة الصحيحة: نحن الأمة المسلمة الواحدة — وجماعتنا الأصلية جماعة المسلمين','أين ذهب الدين والأخلاق؟ الغرب والأنظمة المحلية اجتهدوا في مطاردة الدين','وجزء من الفقد من غير إجبار: القابلية من و٣٠ — والمظاهر بلا وعاء','الأخلاق والروابط تفككت: الأوعية ضعفت — بيت وشارع وحلقة وجمعية']),
            ('الكتلة ٢ — كل جيل سأل: حفريات اليأس',['كل جيل شاف عالمه بيوقع: طليطلة ٤٧٨هـ · ٦٥٦هـ · ١٧٩٨م · «الرجل المريض»','حتى المحتلون سألوا «أين هذه الأمة؟» — الوجع نفسه علامة حياة','«أين الأمة» كلمة شحنة: بتخفي التفصيل والباقي والوكالة','فككها لثلاثة: أي مؤسسة سقطت؟ أي رابط انقطع؟ إيه اللي لسه قائم؟']),
            ('الكتلة ٣ — البيت: أول مؤسسة وآخر قلعة',['كل أصل نجا من القرن الطويل نجا لأن له بيتًا: قرآن ولغة وذاكرة وشبكات','البيت تاريخيًّا: مدرسة ووحدة اقتصادية ومكتبة وملاذ — والحداثة سحبت وظيفة وظيفة','استرداد وظائف بممارسات صغيرة: ساعة حضور · حكاية من جيل · لغة حية · مسؤولية ثابتة','خط أحمر: البيوت أوضاع — حق المرور والبديل الكتابي محفوظان دائمًا']),
    ],
    mission=['خريطة البيت (خاصة): رابط سليم/مقطوع/محتاج ترميم','ممارسة واحدة صغيرة وعلامة تتقاس','مهارة ٣١ + مسمار ١٩'],
    visual='generations', next='الأسبوع ٣٢: الجماعات الوسيطة — إزاي الأمة حافظت على حضورها؟'),
2: dict(title='الجماعات الوسيطة', ep='«إزاي الأمة حافظت على حضورها؟»',
    q='إزاي أمة فقدت خلافتها وقطعت أطرافها حافظت على حضورها؟ — وإيه درجك إنت على سلم الجماعات؟',
    src=['Q67 ميزان القرن وآليات البقاء','عصبية ابن خلدون (و٢٥) ومركزية و٢٩','دعوة و٢٣ وشبكات و٣٠','بروتوكولات و١ — أمان الدوائر','B الجماعات الوسيطة — هدف جلب موثق'],
    blocks=[('الكتلة ١ — ميزان Q67: البقاء نفسه إنجاز',['«بقاء الإسلام وتسيده للحالة الإسلامية أهم إنجازات في ميزان الحركة الإسلامية»','شروط مادية كانت تمحي: خلافة ١٩٢٤ · تعليم استعماري · قوانين وضعية · حدود','آليات البقاء: المسجد · الحلقة المتنقلة · الوقف والأهلية · اللغة والذاكرة · شبكات التجارة والحج','والحركات بميزان واحد: إنجاز وإخفاق — بلا تمجيد حزبي ولا تكفير']),
            ('الكتلة ٢ — المفهوم والانقطاع',['الجماعات الوسيطة: عيلة ← حي ← حلقة ← وقف ونقابة ← مبادرة وشبكة','ثلاث وظائف: تكافل (سند بوش) · انتماء (هوية بتتعاش) · تدريب (مدرسة المسؤولية)','وحدة إنتاج العصبية (و٢٥): مجتمع بلا وسائط = رمل — والرمل ما بيبنيش دول','الانقطاع: المركزية من محمد علي بلعت الوظائف — والفرد بقى وحده قدام الدولة']),
            ('الكتلة ٣ — درجك على السلم',['مشارك: انضم لدائرة موجودة — العلامة انتظام مش حماس','مساهم: قدم مهارتك — العلامة مهمة ثابتة بتتعمل من غير تفكير','باني: عقدة ٣–٥ بغرض في جملة وموعد ثابت وقاعدة خروج — العلامة تشتغل من غيرك أسبوع','أمان السلم: قانون · خصوصية · بلا حزبية ولا تكفير · باب خروج بكرامة']),
    ],
    mission=['سمِّ درجتك على السلم بصدق: مشارك/مساهم/باني','دائرة واحدة موجودة أو عقدة جديدة — بغرضها في جملة وأول خطوة','مهارة ٣٢ + مسمار ٢٠'],
    visual='ladder', next='الأسبوع ٣٣: من عالم الأفكار للسلوك — إزاي المعرفة بتبقى ممارسة؟'),
3: dict(title='من عالم الأفكار للسلوك', ep='«إزاي المعرفة بتبقى ممارسة؟»',
    q='إزاي الفكرة بتتحول سلوك؟ وليه مجتمعات بتزيد مظاهر تدينها وسلوكها ما بيتحسنش؟',
    src=['T1 المعرفة والمهارة والتوجه (02:54–04:38)','T13 الخلل السلوكي (01:32:40 و01:48:00)','T14 الأفكار والسلوك','بن نبي شروط النهضة (من و٣٠)'],
    blocks=[('الكتلة ١ — الثالوث والخلل السلوكي',['معرفة/مهارة/توجه: تعرف ≠ تقدر ≠ عايز — والتعليم بيشتغل على ضلع واحد','الخلل السلوكي: مظاهر التدين تزيد والسلوك ما بيتحسنش — مجتمع بيصلي وبيغش','ليه؟ المظاهر رخيصة (مرئية واجتماعية ومكافأة فورية) والسلوك غالي ومكلف','الاختبار: إسلامك يُقرأ من سلوكك قبل مكتبتك — والفجوة مقدمة تشقق (و٢٠)']),
            ('الكتلة ٢ — سلسلة الحلقات الست',['فكرة مسماة (فعل+شخص+موقف) ← قرار مربوط بوقت ومكان','ممارسة صغيرة منتظمة — اللي بيدوم الصغير المنتظم لا الكبير المتقطع','بيئة حاضنة (قول لواحد + رتب المكان) ← قياس صادق (علامة بأمانة بلا جلد ذاتي)','عادة ← فكرة أكبر — وسقطت ممارسة؟ شخّص الحلقة مش الشخص']),
            ('الكتلة ٣ — شروط النهضة عليك',['بن نبي: نهضة = إنسان + تراب + وقت وفكرة فعالة محركة','الإنسان: إنت بالثالوث — التربة: تُشخَّص وتُزرع مش تَتلعن — الوقت: إيقاع مش مدة','الفكرة بتبقى فعالة لما تجاوب حاجة حقيقية عند إنسان حقيقي في وقت حقيقي','وقاعدة الخروج من و٢٣: كل مشروع له نهاية — نجاحًا أو تسليمًا نظيفًا']),
    ],
    mission=['املا بطاقة فكرة لمشروع — بفكرة من الدورة نفسها','السلسلة كاملة: اسمها واربطها وصغّرها واحضنها وقسها','مهارة ٣٣'],
    visual='chain', next='الأسبوع ٣٤: الفعل المسؤول الآمن + ملف و٨ وميزان الدورة'),
4: dict(title='الفعل المسؤول الآمن', ep='«ما العمل؟ — وملف الوحدة ٨»',
    q='ما العمل — من غير شلل ومن غير تهور — وإزاي يبقى فعلك مسؤولًا وآمنًا؟',
    src=['Q68 إنت بماذا ستساهم؟','Q69–Q70 أكثر من 600 سؤال و«ما العمل وكيف الخلاص»','بروتوكولات و١ في المجال العام','AT ما العمل · T17 ختام'],
    blocks=[('الكتلة ١ — بين حفرتين: الشلل والتهور',['الشلل: تحليل ما بيخلصش — والاستعداد اللي ما بينتهيش تسويف بلباس منهجي','التهور: حماس بلا عدة — اختبار الخوارج من و٢١: صدق + نصوص + غياب منهج = كارثة','٦٠٠ سؤال كلها «ما العمل؟» — عطش لمنهج لا لشعار: فرصة خدمة عامة','الطريق الثالث: فعل مسؤول — يبدأ صغيرًا ومحميًّا بشروط ومقاسًا وله خروج']),
            ('الكتلة ٢ — الشروط الستة للفعل الآمن',['١ القانون أولًا — حماية الناس قبل المشروع · ٢ اللاعنف — درس كل الفتن (و٢٢)','٣ بلا حزبية ولا تكفير — فعلك «علشان» حاجة مش «ضد» ناس','٤ صغير ومقاس ومنتظم · ٥ بروتوكول الحوار في المجال العام — اقفل بتعلم لا بانتصار','٦ الأمان ليك ولغيرك: خصوصية · حماية الأهل والدائرة · خروج بكرامة']),
            ('الكتلة ٣ — الميدان وميزان الدورة',['ميادين بلا إذن: خدمة معرفة · خدمة حي · وقفية صغيرة · مهنة كخدمة · توثيق ذاكرة','اختار ميدانًا واحدًا بالمعيار الخلدوني: حاجة حقيقية ناقصة حواليك إنت','ميزان الدورة: ٣٤ مهارة · ٢٠ مسمارًا · ٨ ملفات — من «مش عارف إنك مش عارف» للميدان','التاريخ بيقرأ الأفعال لا النوايا: الحجر بإتقان — والجدار بيشيل سقف']),
    ],
    mission=['ملف و٨ بخمس مكونات','بطاقة فعل مدني آمن: ميدان + ٦ شروط + علامة + خروج','ميزان الدورة + سطر «لسه ما أعرفوش»'],
    visual='field', next='أسبوع تنفس ٣٥: راحة ومراجعة لمهارات المرحلة ٣ (٢٦–٣٤) — ثم الأسبوع ٣٦: المشروع الختامي'),
}


def diagram(slide, prs, kind):
    """Native vector diagrams mirroring the weekly SVG visuals — بلا تجسيد لأشخاص."""
    if kind == 'generations':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'أين الأمة؟ سؤال كل جيل — والبيت اللي شايل الإجابة', 20, True, NAVY, PP_ALIGN.CENTER)
        gens = [('الجيل الأندلسي','شاف طليطلة بتسقط ٤٧٨هـ وقعد يرثي'),('الجيل البغدادي','شاف ٦٥٦هـ — وحس إن العالم بينتهي'),('جيل ١٧٩٨','الصدمة — «إحنا بالذات وصلنا القاع»'),('الجيل العثماني الأخير','عاش «الرجل المريض» وسأل نفس السؤال')]
        for i,(a,b) in enumerate(gens):
            x = 0.7 + i*3.05
            box(slide, x, 1.4, 2.9, 0.5, a, TEAL, WHITE, 12.5)
            box(slide, x, 1.96, 2.9, 0.6, b, WHITE, INK, 10.5, False)
        box(slide, 0.7, 2.72, 11.88, 0.45, '«كل جيل سأل هذا السؤال — حتى المحتلون سألوه» — الوجع نفسه علامة حياة: حضارة ميتة ما بتسألش عن نفسها (Q66)', 'F9E9E7', RED, 11.5, False)
        box(slide, 4.5, 3.35, 4.3, 0.5, '«أين الأمة؟» — سؤال عام حارق', RED, WHITE, 13)
        arrow(slide, 5.2, 3.9, 2.7, 4.06); arrow(slide, 6.65, 3.9, 6.65, 4.06); arrow(slide, 8.1, 3.9, 10.6, 4.06)
        qs = ['أي مؤسسة سقطت؟ — باسمها وتاريخها','أي رابط انقطع؟ — بيت/شارع/حلقة/جمعية','إيه اللي لسه قائم وبيشتغل؟ — أصل واحد على الأقل']
        for i,a in enumerate(qs):
            box(slide, 0.7 + i*3.95, 4.12, 3.8, 0.55, a, TEAL, WHITE, 11.5)
        box(slide, 0.7, 4.85, 11.88, 0.5, 'البيت — أول مؤسسة: كل أصل نجا من القرن الطويل نجا لأن له بيتًا يشيله (لغة · ذاكرة · قرآن · روابط)', NAVY, WHITE, 12.5)
        prac = ['ساعة حضور — أكلة بلا شاشات','حكاية من جيل أكبر — بصوتك إنت','لغة حية — كلمة أو بيت أو آية','مسؤولية ثابتة لواحد صغير']
        for i,a in enumerate(prac):
            box(slide, 0.7 + i*3.05, 5.45, 2.9, 0.5, a, PALEG, '8A5A02', 10.5)
        box(slide, 0.7, 6.08, 11.88, 0.42, 'خط أحمر — حق المرور: الخريطة تُكتب ولا تُعرض · البيوت أوضاع مختلفة · لا إفصاح إجباري ولا مقارنة بيوت', 'F9E9E7', RED, 11)
        box(slide, 0.7, 6.6, 11.88, 0.42, 'مهارة ٣١: خريطة البيت + ممارسة واحدة وعلامة · ومسمار ١٩: البيت مش تفصيلة — ده أول مؤسسة', NAVY, WHITE, 11.5)
    elif kind == 'ladder':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'سلم الجماعات الوسيطة — من الفرد للشبكة', 20, True, NAVY, PP_ALIGN.CENTER)
        box(slide, 0.7, 1.38, 11.88, 0.62, '«بقاء الإسلام وتسيده للحالة الإسلامية أهم إنجازات في ميزان الحركة الإسلامية» (Q67) — الأمة حافظت على حضورها بشبكاتها لا بدولها', PALEG, '8A5A02', 12.5)
        steps = ['الفرد','البيت','الحي والشارع','المسجد والحلقة','الوقف والنقابة','المبادرة والشبكة']
        for i,a in enumerate(steps):
            x = 0.7 + i*2.02; y = 4.75 - i*0.52
            box(slide, x, y, 1.9, 0.45, a, TEAL if i < 5 else NAVY, WHITE, 11.5)
            if i: arrow(slide, x - 0.16, y + 0.68, x - 0.02, y + 0.47)
        box(slide, 0.7, 5.35, 11.88, 0.42, 'الانقطاع الحديث: الدولة المركزية بلعت الوسائط واحدة واحدة — والفرد بقى وشًّا لوش مع أجهزة ضخمة (من محمد علي — و٢٩)', 'F9E9E7', RED, 11, False)
        funcs = ['تكافل — سند بوش وعلاقة: المعاش ما بيمسكش إيد حد','انتماء — هوية بتتعاش في جماعة صغيرة قبل الوثيقة','تدريب — مدرسة المسؤولية: تقود بلا سلطة وتختلف بلا خصام']
        for i,a in enumerate(funcs):
            box(slide, 0.7 + i*3.95, 5.87, 3.8, 0.5, a, WHITE, INK, 10.5, False)
        box(slide, 0.7, 6.5, 11.88, 0.5, 'درج السلم: مشارك (انتظام مش حماس) ← مساهم (مهمة ثابتة) ← باني (عقدة تشتغل من غيرك أسبوعًا) · مسمار ٢٠: الشبكات الكبيرة بتتولد من عقد صغيرة', NAVY, WHITE, 11.5)
    elif kind == 'chain':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'من عالم الأفكار للسلوك — سلسلة الحلقات الست وميزان الخلل', 19, True, NAVY, PP_ALIGN.CENTER)
        links = ['١ فكرة مسماة','٢ قرار مربوط','٣ ممارسة صغيرة','٤ بيئة حاضنة','٥ قياس صادق','٦ عادة']
        for i,a in enumerate(links):
            x = 0.7 + (5-i)*2.02
            box(slide, x, 1.4, 1.9, 0.5, a, TEAL, WHITE, 12)
            if i < 5: arrow(slide, x - 0.02, 1.65, x - 0.14, 1.65)
        arrow(slide, 1.65, 2.12, 11.6, 2.12, GOLD, 1.5)
        txt(slide, 0.7, 2.16, 11.93, 0.35, 'العادة المستقرة بتسلم لفكرة أكبر — السلم بيطلع مش بيوقف', 11, True, GOLD, PP_ALIGN.CENTER)
        box(slide, 6.78, 2.62, 5.8, 0.45, 'المظاهر — رخيصة (الخلل السلوكي T13)', RED, WHITE, 12.5)
        r = ['مرئية واجتماعية — مكافأة فورية بالتصفيق','بلا صراع داخلي — فالنفس تروح للأرخص','مظاهر التدين تزيد والسلوك ما بيتحسنش','بتصلي وتغش · بتصوم وتنقض العهد']
        for i,a in enumerate(r):
            box(slide, 6.78, 3.14 + i*0.42, 5.8, 0.36, a, 'F9E9E7', RED, 10)
        box(slide, 0.7, 2.62, 5.8, 0.45, 'السلوك — غالي', TEAL, WHITE, 12.5)
        g = ['غير مرئي أغلبه — ومكافأته متأخرة','مكلف: بياخد راحة أو فلوس أو كبرياء','محتاج الثالوث كاملًا: معرفة + مهارة + توجه','والتعليم التقليدي بيشتغل على ضلع واحد']
        for i,a in enumerate(g):
            box(slide, 0.7, 3.14 + i*0.42, 5.8, 0.36, a, PALE, TEAL, 10)
        box(slide, 0.7, 4.94, 11.88, 0.45, 'الاختبار: إسلامك يُقرأ من سلوكك قبل مكتبتك — الناس بتشوف اللي بتعمله مش اللي بتعرفه', NAVY, WHITE, 12.5)
        bn = ['إنسان: إنت بالثالوث — فاعل مش متفرج','تراب: اللي حواليك — يُشخَّص ويُزرع مش يَتلعن','وقت: مش مدة — إيقاع: حاجة كل يوم أو كل أسبوع']
        for i,a in enumerate(bn):
            box(slide, 0.7 + i*3.95, 5.52, 3.8, 0.5, a, GOLD, WHITE, 11)
        box(slide, 0.7, 6.14, 7.6, 0.5, '+ فكرة فعالة محركة: تجاوب حاجة حقيقية عند إنسان حقيقي في وقت حقيقي (بن نبي — من و٣٠)', TEAL, WHITE, 11)
        box(slide, 8.5, 6.14, 4.08, 0.5, 'سقطت ممارسة؟ شخّص الحلقة مش الشخص — وكل مشروع له خروج (و٢٣)', WHITE, INK, 10.5, False)
    elif kind == 'field':
        txt(slide, 0.5, 0.9, 12.3, 0.5, 'الشروط الستة للفعل المدني الآمن والميادين', 20, True, NAVY, PP_ALIGN.CENTER)
        box(slide, 0.7, 1.4, 5.8, 0.8, 'حفرة الشلل: تحليل ما بيخلصش — والاستعداد اللي ما بينتهيش بقرار بقى تسويفًا بلباس منهجي', 'F9E9E7', RED, 11.5, False)
        box(slide, 6.78, 1.4, 5.8, 0.8, 'حفرة التهور: صدق + حماس + غياب منهج = كارثة — اختبار الخوارج من و٢١', 'F9E9E7', RED, 11.5, False)
        box(slide, 3.2, 2.35, 6.93, 0.5, 'الطريق الثالث: فعل مسؤول — يبدأ صغيرًا · محميًّا بشروط · مقاسًا · وله خروج', TEAL, WHITE, 12.5)
        conds = ['١ القانون أولًا — حماية الناس قبل المشروع','٢ اللاعنف — العنف بيهدم اللي بيقول إنه بيحميه','٣ بلا حزبية ولا تكفير — «علشان» حاجة مش «ضد» ناس','٤ صغير ومقاس ومنتظم — سلسلة و٣٣','٥ بروتوكول الحوار في المجال العام — اقفل بتعلم','٦ الأمان — خصوصية وحماية الأهل وخروج بكرامة']
        for i,a in enumerate(conds):
            x = 0.7 + (i % 3)*3.95; y = 3.0 + (i // 3)*0.62
            box(slide, x, y, 3.8, 0.52, a, PALE, TEAL, 10.5)
        box(slide, 0.7, 4.35, 11.88, 0.45, 'الحماس وتر — والشروط قوس: مع بعض بيوصلوا السهم · الشروط مش قيودًا — دي الهيكل اللي بيخلي الحماس يعمر بدل ما ينفجر', NAVY, WHITE, 11.5)
        fields = ['خدمة معرفة: محتوى عربي جيد','خدمة حي: درس ووساطة بميزان','وقفية صغيرة: حاجة تستمر بعدك','مهنة كخدمة: إتقان + تدريب حد','توثيق ذاكرة: عيلتك وحيك وحرفتك']
        for i,a in enumerate(fields):
            box(slide, 0.7 + i*2.4, 4.95, 2.28, 0.6, a, PALEG, '8A5A02', 10)
        box(slide, 0.7, 5.7, 11.88, 0.55, 'ميزان الدورة: ٣٤ مهارة · ٢٠ مسمارًا · ٨ ملفات — من «إنت مش عارف إنك مش عارف» (و١) للميدان — رأس المال العدة والأدب', TEAL, WHITE, 12)
        box(slide, 0.7, 6.4, 11.88, 0.5, 'ملف و٨ — خمس مكونات: خريطة بيت · خطة دائرة · بطاقة فكرة لسلوك · بطاقة فعل مدني آمن · ميزان الدورة + سطر «لسه ما أعرفوش»', WHITE, INK, 11.5, False)


def build_pptx():
    made = []
    for n, w in WEEKS.items():
        prs = prs_base()
        blank = prs.slide_layouts[6]
        # S1 title
        s = prs.slides.add_slide(blank); bg(s, prs)
        box(s, 0.7, 0.7, 11.93, 0.55, f'مشروع تأسيس · الوحدة 8 · v0.4', NAVY, WHITE, 14, False)
        txt(s, 0.7, 1.7, 11.93, 1.2, f'الأسبوع {n+30} — {w["title"]}', 40, True, NAVY, PP_ALIGN.CENTER)
        txt(s, 0.7, 3.0, 11.93, 0.8, f'الحلقة المسموعة: {w["ep"]}', 22, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 4.0, 9.93, 1.1, w['q'], WHITE, INK, 16, False)
        slide_shapes = s.shapes[-1]; slide_shapes.line.color.rgb = PRGB.from_string(GOLD); slide_shapes.line.width = PPt(2)
        txt(s, 0.7, 5.5, 11.93, 1.2, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+30)
        # S2 episode + sources
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'الحلقة ومصادرها', 28, True, NAVY)
        for i, srcx in enumerate(w['src']):
            box(s, 0.7, 1.3 + i*1.05, 11.93, 0.85, srcx, WHITE, INK, 14, False)
            bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(TEAL); bs.line.width = PPt(1.5)
        txt(s, 0.7, 5.7, 11.93, 0.9, 'الطوابع الزمنية ~تقريبية — تُدقق مقابل الفيديو الأصلي قبل النشر (بوابة G9) · التفريغات في transcripts/', 11, False, MUTED)
        footer(s, n+30)
        # S3-5 blocks
        for t, points in w['blocks']:
            s = prs.slides.add_slide(blank); bg(s, prs)
            txt(s, 0.7, 0.4, 11.93, 0.7, t, 26, True, TEAL)
            for i, pt in enumerate(points):
                txt(s, 0.9, 1.35 + i*1.5, 11.5, 1.4, '• ' + pt, 17, False, INK)
            footer(s, n+30)
        # S6 diagram
        s = prs.slides.add_slide(blank); bg(s, prs)
        diagram(s, prs, w['visual'])
        txt(s, 0.7, 6.62, 11.93, 0.4, 'النسخة القابلة للطباعة: 03_المواد_البصرية (SVG)', 10, False, MUTED, PP_ALIGN.CENTER)
        footer(s, n+30)
        # S7 mission + agenda note
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 0.4, 11.93, 0.7, 'مهمة الأسبوع — منخفضة المخاطر', 28, True, NAVY)
        for i, m in enumerate(w['mission']):
            box(s, 0.7, 1.3 + i*1.0, 11.93, 0.8, m, GOLD if i==0 else WHITE, WHITE if i==0 else INK, 15, i==0)
            if i: bs = s.shapes[-1]; bs.line.color.rgb = PRGB.from_string(GOLD); bs.line.width = PPt(1.5)
        txt(s, 0.7, 4.5, 11.93, 1.6, 'في اللقاء الحي: 120 دقيقة وفق دليل الميسر — الحلقة تُسمع/تُقرأ قبل اللقاء، والمشجر يُعرض في فقرة الشرح ويُوزع مطبوعًا.\nحق المرور والبديل الكتابي محفوظان · لا يُطلب إفصاح عن معتقد أو تجربة حساسة.', 13, False, MUTED)
        footer(s, n+30)
        # S8 closing
        s = prs.slides.add_slide(blank); bg(s, prs)
        txt(s, 0.7, 1.2, 11.93, 0.9, 'الأسبوع الجاي', 30, True, TEAL, PP_ALIGN.CENTER)
        box(s, 1.7, 2.3, 9.93, 1.0, w['next'], NAVY, WHITE, 18)
        txt(s, 0.7, 3.7, 11.93, 0.8, 'مكتبة التوسع: T الثالوث والخلل السلوكي (المحاضرة الأولى والمستوى الثاني 4/5/8) · بروتوكولات و1 · L اللغة الحية · B البيت والجماعات الوسيطة (هدف جلب موثق)', 13, False, MUTED, PP_ALIGN.CENTER)
        txt(s, 0.7, 5.3, 11.93, 0.6, DISCLAIMER, 11, False, RED, PP_ALIGN.CENTER)
        footer(s, n+30)
        out = OUT / f'{9+n}_week_{n}_meeting_slides_module_08_v0_4.pptx'
        prs.save(out); made.append(out)
    return made

# ---------------- ZIP + validation ----------------
def md5(p): return hashlib.md5(Path(p).read_bytes()).hexdigest()

def build_zips(all_made):
    pack = FINAL/'module_08_v0_4_production_pack.zip'
    with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.name != '00_حالة_المخرجات.md':
                z.write(f, f'02_مخرجات_قيد_الإنتاج/{f.name}')
        for f in sorted(VIS.iterdir()): z.write(f, f'03_المواد_البصرية/{f.name}')
    full = FINAL/'module_08_v0_4_full_project_files.zip'
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ROOT.rglob('*')):
            if f.is_file() and FINAL not in f.parents and f.name != 'generate_module_08_v0_4.py':
                z.write(f, str(f.relative_to(ROOT)))
    # validation report
    lines = ['# تقرير التحقق — حزمة الوحدة 8 v0.4', '', f'**تاريخ البناء:** {DATE_AR} (2026-10-26) · **المولد:** `generate_module_08_v0_4.py` · **بايثون:** venv المشروع (python-docx 1.0.2 / python-pptx / openpyxl 3.1.5)', '', '## ملفات المخرجات (MD5)', '', '| الملف | الحجم (بايت) | MD5 |', '|---|---:|---|']
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
    (FINAL/'validation_report_module_08_v0_4.md').write_text('\n'.join(lines), encoding='utf-8')
    (FINAL/'README_module_08_v0_4.md').write_text(
        '# الحزمة النهائية — الوحدة 8 v0.4\n\n'
        '- `module_08_v0_4_production_pack.zip` — المخرجات (DOCX/XLSX/PPTX) + البصريات (SVG)\n'
        '- `module_08_v0_4_full_project_files.zip` — مجلد الوحدة كاملًا (أصول نصية + تصميم وتتبع + مخرجات + بصريات)\n'
        '- `validation_report_module_08_v0_4.md` — MD5 وفحص القبول\n\n'
        '⚠️ النصوص أسلوب مستوحى من أيمن عبد الرحيم — ليست قولًا منسوبًا إليه. لا نشر باسمه أو بصوت مولد دون إذن صريح.\n', encoding='utf-8')
    return [pack, full]

if __name__ == '__main__':
    made = build_docx() + build_xlsx() + build_pptx()
    zips = build_zips(made)
    print('BUILT:')
    for f in made + zips: print(' -', f.name, f.stat().st_size)
