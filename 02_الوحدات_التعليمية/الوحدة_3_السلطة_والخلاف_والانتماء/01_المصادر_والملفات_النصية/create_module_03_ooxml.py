from pathlib import Path
import csv
import re
import zipfile
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from pptx import Presentation
from pptx.util import Inches, Pt as PPTPt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor as PPTRGB

ROOT = Path('/home/user/module_03_power_conflict_belonging')
OUT = ROOT / 'deliverables'
SLIDES = OUT / 'slides'
OUT.mkdir(exist_ok=True)
SLIDES.mkdir(exist_ok=True)

AR_FONT = 'Arial'
NAVY = '13293D'
TEAL = '007C7A'
GOLD = 'E5A44D'
LIGHT = 'F6F3EE'
DARK = '17212B'
MUTED = '51606D'

# ---------------- DOCX ----------------
def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tcPr.append(shd)

def set_cell_text(cell, text, bold=False, color=None):
    cell.text = ''
    p = cell.paragraphs[0]
    set_rtl(p, right=True)
    r = p.add_run(str(text))
    r.bold = bold
    set_run_font(r, 9.0, color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def set_run_font(run, size=10.5, color=None):
    run.font.name = AR_FONT
    run._element.rPr.rFonts.set(qn('w:ascii'), AR_FONT)
    run._element.rPr.rFonts.set(qn('w:hAnsi'), AR_FONT)
    run._element.rPr.rFonts.set(qn('w:cs'), AR_FONT)
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)

def set_rtl(paragraph, right=True):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.LEFT
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1' if right else '0')
    pPr.append(bidi)

def add_para(doc, text='', style=None, level=None, bullet=False, numbered=False, mono=False):
    if style:
        p = doc.add_paragraph(style=style)
    elif bullet:
        p = doc.add_paragraph(style='List Bullet')
    elif numbered:
        p = doc.add_paragraph(style='List Number')
    else:
        p = doc.add_paragraph()
    set_rtl(p)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = text.replace('**', '').replace('__', '').replace('*', '')
    r = p.add_run(text)
    set_run_font(r, 10 if bullet or numbered else 10.5)
    if mono:
        r.font.name = 'Courier New'
        r._element.rPr.rFonts.set(qn('w:ascii'), 'Courier New')
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    return p

def parse_table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith('|'):
        row = [c.strip() for c in lines[i].strip().strip('|').split('|')]
        rows.append(row)
        i += 1
    if len(rows) > 1 and all(re.match(r'^:?-{3,}:?$', c.replace(' ', '')) for c in rows[1]):
        rows.pop(1)
    return rows, i

def add_md_table(doc, rows):
    if not rows:
        return
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    for ri, row in enumerate(rows):
        cells = table.add_row().cells
        for ci in range(cols):
            value = row[ci] if ci < len(row) else ''
            set_cell_text(cells[ci], value, bold=(ri == 0), color='FFFFFF' if ri == 0 else None)
            if ri == 0:
                set_cell_shading(cells[ci], NAVY)
            elif ri % 2 == 0:
                set_cell_shading(cells[ci], 'EEF3F4')
    doc.add_paragraph()

def make_docx(md_name, out_name, title, subtitle):
    text = (ROOT / md_name).read_text(encoding='utf-8')
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(1.7); sec.bottom_margin = Cm(1.5); sec.left_margin = Cm(1.5); sec.right_margin = Cm(1.5)
    # default styles
    styles = doc.styles
    styles['Normal'].font.name = AR_FONT
    styles['Normal']._element.rPr.rFonts.set(qn('w:cs'), AR_FONT)
    styles['Normal'].font.size = Pt(10.5)
    for name, size, color in [('Title', 26, NAVY), ('Heading 1', 18, NAVY), ('Heading 2', 14, TEAL), ('Heading 3', 12, GOLD)]:
        st = styles[name]
        st.font.name = AR_FONT
        st._element.rPr.rFonts.set(qn('w:cs'), AR_FONT)
        st.font.size = Pt(size)
        st.font.color.rgb = RGBColor.from_string(color)
    # header/footer
    hp = sec.header.paragraphs[0]
    set_rtl(hp); rr = hp.add_run('من اليقين إلى الوعي والعمل — الوحدة 3'); set_run_font(rr, 8.5, TEAL)
    fp = sec.footer.paragraphs[0]
    set_rtl(fp); rr = fp.add_run('مسودة إنتاجية v0.1 — 25 أكتوبر 2026'); set_run_font(rr, 8, MUTED)
    # cover
    p = doc.add_paragraph(); set_rtl(p)
    p.paragraph_format.space_before = Pt(90)
    r = p.add_run(title); set_run_font(r, 27, NAVY); r.bold = True
    p2 = doc.add_paragraph(); set_rtl(p2)
    r = p2.add_run(subtitle); set_run_font(r, 15, TEAL)
    p3 = doc.add_paragraph(); set_rtl(p3)
    r = p3.add_run('مسودة إنتاجية v0.1 | العربية | 25 أكتوبر 2026'); set_run_font(r, 10.5, MUTED)
    doc.add_page_break()
    lines = text.splitlines()
    i = 0; in_code = False
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        if line.startswith('```'):
            in_code = not in_code; i += 1; continue
        if in_code:
            add_para(doc, line, mono=True); i += 1; continue
        if line.strip().startswith('|'):
            rows, i = parse_table(lines, i); add_md_table(doc, rows); continue
        if not line.strip() or line.startswith('---'):
            i += 1; continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            lvl = len(m.group(1)); head = m.group(2)
            if lvl == 1:
                p = doc.add_paragraph(style='Heading 1')
            elif lvl == 2:
                p = doc.add_paragraph(style='Heading 2')
            else:
                p = doc.add_paragraph(style='Heading 3')
            set_rtl(p); r = p.add_run(head); set_run_font(r, {1:18,2:14,3:12,4:11}[lvl], {1:NAVY,2:TEAL,3:GOLD,4:DARK}[lvl]); r.bold=True
            p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(5)
        elif re.match(r'^\s*[-*]\s+', line):
            add_para(doc, re.sub(r'^\s*[-*]\s+', '', line), bullet=True)
        elif re.match(r'^\s*\d+\.\s+', line):
            add_para(doc, re.sub(r'^\s*\d+\.\s+', '', line), numbered=True)
        elif line.startswith('>'):
            p = add_para(doc, line[1:].strip())
            for r in p.runs: r.italic = True; r.font.color.rgb = RGBColor.from_string(TEAL)
        else:
            add_para(doc, line)
        i += 1
    path = OUT / out_name
    doc.save(path)
    return path

# ---------------- XLSX ----------------
def csv_to_xlsx(csv_name, xlsx_name, sheet_name):
    in_path = ROOT / csv_name
    rows = list(csv.reader(in_path.open(encoding='utf-8-sig', newline='')))
    wb = Workbook(); ws = wb.active; ws.title = sheet_name
    for row in rows:
        ws.append(row)
    header_fill = PatternFill('solid', fgColor=NAVY)
    thin = Side(style='thin', color='D6DEE3')
    for cell in ws[1]:
        cell.fill = header_fill; cell.font = Font(name=AR_FONT, color='FFFFFF', bold=True)
        cell.alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name=AR_FONT, size=10)
            cell.alignment = Alignment(horizontal='right', vertical='top', wrap_text=True)
            cell.border = Border(bottom=thin)
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    for idx, col in enumerate(ws.columns, 1):
        max_len = max(len(str(c.value or '')) for c in col)
        ws.column_dimensions[chr(64+idx) if idx <= 26 else 'A'].width = min(max(max_len * 0.9, 12), 45)
    ws.row_dimensions[1].height = 32
    # add Excel table if range sane
    if ws.max_row > 1 and ws.max_column > 0:
        from openpyxl.utils import get_column_letter
        ref = f'A1:{get_column_letter(ws.max_column)}{ws.max_row}'
        tab = Table(displayName='DataTable', ref=ref)
        tab.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
        ws.add_table(tab)
    path = OUT / xlsx_name
    wb.save(path)
    return path

# ---------------- PPTX ----------------
def ppt_set_rtl(paragraph, align=PP_ALIGN.RIGHT, size=20, color='17212B', bold=False):
    paragraph.alignment = align
    paragraph.level = 0
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set('rtl', '1')
    for r in paragraph.runs:
        r.font.name = AR_FONT; r.font.size = PPTPt(size); r.font.bold = bold; r.font.color.rgb = PPTRGB.from_string(color)

def add_textbox(slide, x, y, w, h, text, size=20, color=DARK, bold=False, align=PP_ALIGN.RIGHT, fill=None, border=None):
    if fill:
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        shape.fill.solid(); shape.fill.fore_color.rgb = PPTRGB.from_string(fill)
        shape.line.color.rgb = PPTRGB.from_string(border or fill)
        tf = shape.text_frame
    else:
        shape = slide.shapes.add_textbox(x, y, w, h)
        tf = shape.text_frame
    tf.clear(); tf.word_wrap = True; tf.margin_left = Inches(.13); tf.margin_right=Inches(.13); tf.margin_top=Inches(.08); tf.margin_bottom=Inches(.08)
    lines = text.split('\n')
    for idx, line in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = line
        ppt_set_rtl(p, align, size, color, bold)
        p.space_after = PPTPt(5)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return shape

def add_bg(slide, week, title, subtitle=''):
    bg = slide.background.fill; bg.solid(); bg.fore_color.rgb = PPTRGB.from_string(LIGHT)
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(.42))
    band.fill.solid(); band.fill.fore_color.rgb = PPTRGB.from_string(NAVY); band.line.fill.background()
    slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(11.85), Inches(.42), Inches(1.483), Inches(.10)).fill.solid()
    accent = slide.shapes[-1]; accent.fill.fore_color.rgb = PPTRGB.from_string(GOLD); accent.line.fill.background()
    add_textbox(slide, Inches(.55), Inches(.70), Inches(12.25), Inches(.60), title, 25, NAVY, True)
    if subtitle: add_textbox(slide, Inches(.6), Inches(1.31), Inches(12), Inches(.35), subtitle, 10.5, MUTED)
    add_textbox(slide, Inches(.55), Inches(7.12), Inches(12.25), Inches(.22), f'الوحدة 3 — السلطة والخلاف والانتماء في التاريخ المبكر | الأسبوع {week} | مسودة إنتاجية v0.1', 7.5, MUTED)

def add_bullets(slide, bullets, y=Inches(1.9), x=Inches(.75), w=Inches(11.7), h=Inches(4.7), size=18, color=DARK):
    text = '\n'.join([f'• {b}' for b in bullets])
    add_textbox(slide, x, y, w, h, text, size, color, False)

def slide_deck(week, filename, slides):
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    for spec in slides:
        layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(layout)
        add_bg(slide, week, spec['title'], spec.get('subtitle',''))
        if spec.get('type') == 'two':
            add_textbox(slide, Inches(.7), Inches(1.9), Inches(5.85), Inches(4.7), spec['left_title'], 16, 'FFFFFF', True, fill=TEAL)
            add_textbox(slide, Inches(.85), Inches(2.55), Inches(5.55), Inches(3.7), '\n'.join('• '+b for b in spec['left']), 16, DARK)
            add_textbox(slide, Inches(6.8), Inches(1.9), Inches(5.85), Inches(4.7), spec['right_title'], 16, 'FFFFFF', True, fill=NAVY)
            add_textbox(slide, Inches(6.95), Inches(2.55), Inches(5.55), Inches(3.7), '\n'.join('• '+b for b in spec['right']), 16, DARK)
        elif spec.get('type') == 'quote':
            add_textbox(slide, Inches(1.2), Inches(2.0), Inches(10.9), Inches(2.1), spec['quote'], 25, NAVY, True, align=PP_ALIGN.CENTER, fill='FFFFFF', border='D9E3E5')
            add_textbox(slide, Inches(1.4), Inches(4.45), Inches(10.5), Inches(1.15), spec.get('prompt',''), 16, TEAL, False, align=PP_ALIGN.CENTER)
        elif spec.get('type') == 'steps':
            labels=spec['steps']; n=len(labels); gap=11.6/n
            for i,label in enumerate(labels):
                xx=Inches(.75+i*gap)
                circ=slide.shapes.add_shape(MSO_SHAPE.OVAL,xx,Inches(2.35),Inches(.65),Inches(.65))
                circ.fill.solid(); circ.fill.fore_color.rgb=PPTRGB.from_string(TEAL if i%2==0 else GOLD); circ.line.fill.background()
                add_textbox(slide,xx,Inches(2.43),Inches(.65),Inches(.25),str(i+1),12,'FFFFFF',True,PP_ALIGN.CENTER)
                add_textbox(slide,xx-Inches(.3),Inches(3.2),Inches(1.25),Inches(1.1),label,14,NAVY,True,PP_ALIGN.CENTER)
                if i<n-1:
                    arr=slide.shapes.add_shape(MSO_SHAPE.CHEVRON,xx+Inches(.75),Inches(2.54),Inches(.48),Inches(.25))
                    arr.fill.solid(); arr.fill.fore_color.rgb=PPTRGB.from_string('AAB8BD'); arr.line.fill.background()
            if spec.get('note'):
                add_textbox(slide, Inches(1), Inches(5.25), Inches(11.3), Inches(.7), spec['note'], 14, MUTED, False, PP_ALIGN.CENTER)
        else:
            add_bullets(slide, spec.get('bullets',[]), size=spec.get('size',18))
    path = SLIDES / filename; prs.save(path); return path


# ---------------- Deck content: Module 3 ----------------
week9 = [
 {'title':'الأسبوع 9 | الفتنة: زمن، رواية، وذاكرة لاحقة','subtitle':'نقرأ تاريخاً شديد الحساسية بلا سبّ ولا يقين متعجل','type':'quote','quote':'«ليس كل ما نتلقاه عن الماضي واقعةً محققة؛ وقد يكون روايةً أو تفسيراً أو حكماً لاحقاً.»','prompt':'خيار المرور محفوظ. لا نطلب من أحد كشف هوية أو موقف أو دفاع عن جماعة.'},
 {'title':'مهارة اليوم وأثرها','type':'two','left_title':'مهارة تاريخية','left':['تمييز الواقعة المزعومة عن الرواية','تسمية المصدر والموضع','وضع حد واضح لما نعرف'], 'right_title':'حوار مسؤول','right':['لا نعمم على جماعات','لا نحول التاريخ إلى معركة هوية','نسأل قبل أن نحكم']},
 {'title':'أربع طبقات قبل أي جواب','type':'steps','steps':['واقعة مزعومة','رواية/مصدر','تفسير','حكم/استعمال'],'note':'قد تجتمع الطبقات في جملة واحدة؛ مهمتنا فصلها لا إنكار أحدها.'},
 {'title':'بروتوكول التاريخ الحساس','type':'steps','steps':['أوقف','صغ العبارة','سمِّ المصدر','ضع الزمن','اذكر الحد'],'note':'إذا تحولت الجلسة إلى استهداف أو تجريح: نتوقف، نعود إلى الكرامة، ونستبدل الحالة.'},
 {'title':'مادة الأسبوع | قراءة لا محكمة','subtitle':'100 سؤال 18–21 | السجل M3-S01 إلى M3-S04','bullets':['الحلقات تمثل عرضاً حجاجياً لمقدميها، والتفريغات آلية.','نحلل كيف تُصاغ الدعوى وما الذي تحتاجه من مصدر ونطاق.','لا نستعمل الحلقة 21 لتصنيف أفراد أو جماعات حاضرة.','لا تقتبس تفريغاً قبل مراجعة موضعه في المادة الأصلية.'], 'size':17},
 {'title':'نشاط B1 | خط زمني متعدد الطبقات','bullets':['رتبوا 5 بطاقات: واقعة مزعومة، مصدر، تفسير، سؤال، تلقي لاحق.','ضعوا علامة استفهام عند كل نقطة لم يثبت موضعها بعد.','أضيفوا سطراً: «هذه الخريطة لا تثبت وحدها ____».','المخرج ليس جواباً طائفياً؛ بل خريطة منصفة ومحدودة.'], 'size':18},
 {'title':'تبديل العدسة','type':'two','left_title':'اسأل المصدر','left':['من نقل؟ متى؟ ولأي جمهور؟','ماذا يقول مباشرة؟'], 'right_title':'اسأل التفسير','right':['ما الافتراض المضاف؟','ما البديل أو الحد؟']},
 {'title':'بطاقة الخروج','bullets':['دعوى لا أستطيع الجزم بها بعد: __________________.','المصدر أو الموضع الذي أحتاجه: __________________.','هل استطعت السؤال أو المرور بأمان؟ 1–5.','وضوح/عبء التحضير: 1–5 / 1–5.'], 'size':19},
]
week10 = [
 {'title':'الأسبوع 10 | السلطة والمعايير: الادعاء لا الشخصنة','subtitle':'نحلل دعوى عن السلطة من دون تحويل التاريخ إلى وصفة للحاضر','type':'quote','quote':'«في هذا المصدر وفي هذا النطاق، يدعم الدليل توصيفاً محدوداً؛ ولا يكفي وحده لحكم شامل.»','prompt':'نناقش ادعاءً، لا نسباً أو هوية أو ولاءً.'},
 {'title':'ما الذي نحتاجه لحكم منصف؟','type':'steps','steps':['دعوى','نطاق','دليل','معيار','بديل','حد'],'note':'المعيار الأخلاقي أو السياسي يجب أن يكون معلناً، لا متخفياً في كلمة كبيرة.'},
 {'title':'كلمات كبيرة تحتاج تفكيكاً','type':'two','left_title':'اسأل عن المعنى','left':['«شرعي»: لمن وبأي معيار؟','«عادل»: في أي سياسة/سياق؟','«قوي»: عسكرياً أم إدارياً أم رمزياً؟'], 'right_title':'ولا تفترض','right':['الحكم الشامل من واقعة','تطابق القوة مع العدالة','تطابق الماضي مع الحاضر']},
 {'title':'مادة الأسبوع | خريطة مرحلة لا خطاب حسم','subtitle':'100 سؤال 22–26 | السجل M3-S05 إلى M3-S09','bullets':['استعملوا حلقة 22 لخريطة أولية، و23–26 لصياغة دعاوى محدودة.','القضايا المتعلقة بالحسين/يزيد/المدينة/مكة حساسة جداً: حالة افتراضية بديلة متاحة.','لا تستنتج المواد نموذج حكم معاصر أو حكماً على كل الدولة/كل الناس.'], 'size':17},
 {'title':'نشاط B3 | محاكمة الادعاء','type':'steps','steps':['صغ الدعوى','حدد النطاق','افحص المصدر','اعرض بديلاً','اكتب الحد'],'note':'الأدوار: محقق مصدر، محدد نطاق، قارئ بديل، حارس كرامة، مقرر.'},
 {'title':'نموذج صياغة','type':'quote','quote':'«في المصدر ____، وعن الفترة ____، تذكر السياسة/الواقعة ____. وقد تدعم توصيفاً محدوداً لـ____، لكنها لا تثبت وحدها ____.»','prompt':'اسأل دائماً: ما الذي يلزم قبل الانتقال من حالة إلى حكم شامل؟'},
 {'title':'من تاريخ إلى حياة رقمية','bullets':['قبل مشاركة قصة تاريخية: من المصدر؟ أين الموضع؟ ما النطاق؟','ميّز بين اقتباس وتفسير وتعليق أخلاقي.','لا تستخدم تاريخاً حساساً لإحراج أو تصنيف شخص حاضر.','التجربة: أعد كتابة منشور متسرع بصياغة تحقق وإنصاف.'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['اكتب صياغة منصفة لاعتراض قوي.','ما معياري المعلن في هذا التقييم؟','ما الحد الذي يمنعني من التعميم؟','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week11 = [
 {'title':'الأسبوع 11 | خريطة النظم: القوة والمعرفة والصراع','subtitle':'فاعل واحد ليس تفسيراً كاملاً، وعامل واحد ليس قدراً','type':'quote','quote':'«التفسير الجيد يبين علاقة وآلية وحداً؛ لا يكتفي باسم بطل أو سبب واحد.»','prompt':'الخريطة أداة سؤال، لا آلة لتوقع السياسة أو لتبريرها.'},
 {'title':'الفارق الضروري','type':'two','left_title':'لا تخلط','left':['الفاعل بالسبب','العلاقة بالضرورة','التفسير بالتبرير'], 'right_title':'ابنِ بدلاً منه','right':['عقداً وعلاقات','مصدر/افتراض لكل سهم','صوتاً غائباً وحداً']},
 {'title':'عقد يمكن أن نراها','type':'steps','steps':['سلطة','نخب','جيش','اقتصاد','علم/تعليم','عامة/أطراف'],'note':'أضفوا ما تحتاجه الحالة، ولا تجعلوا أي عقدة كتلة موحدة.'},
 {'title':'مادة الأسبوع | ما الذي تغيّره البنية؟','subtitle':'100 سؤال 27–31 | السجل M3-S10 إلى M3-S14','bullets':['الحلقات مواد لتمرين شبكة عوامل: تنظيم، تعاقب، عسكر، صورة الحاكم.','لا تنسبوا «إرادة» موحدة إلى دولة أو جيش أو علماء.','حللوا السرد عن هارون الرشيد بوصفه سؤال صورة/مصدر، لا حكماً شخصياً نهائياً.'], 'size':17},
 {'title':'نشاط B4 | خريطة النظم','bullets':['ارسموا 6–8 عقد، ثم ثلاثة أسهم فقط في البداية.','ضعوا (د) للسهم المدعوم بدليل و(ف) للسهم الافتراضي.','أحيطوا عاملاً أو صوتاً غائباً بدائرة.','كل سهم: ما الآلية؟ ما الذي قد ينفيه أو يحده؟'], 'size':18},
 {'title':'اختبار عامل واحد','type':'two','left_title':'عبارة ضعيفة','left':['«شخص واحد يفسر كل تحول.»','«عامل اقتصادي يفسر كل شيء.»'], 'right_title':'إعادة بناء','right':['عاملون + بنى + سياق','علاقة محتملة + دليل + حد']},
 {'title':'تطبيق حياتي محدود','bullets':['عندما يروي خبر عام سبباً واحداً، اسأل: ما العامل الغائب؟','استخدم الخريطة لفهم مؤسسة صغيرة، لا لتسمية خصوم سياسيين.','اكتب: «قد يؤثر ___ في ___ عبر ___، لكن لا أجزم لأن ___.»'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['عاملان وعلاقة واحدة مدعومة أو مفترضة.','صوت أو عنصر غائب من الخريطة.','الفرق الذي سأحافظ عليه: سبب / تزامن / تبرير.','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week12 = [
 {'title':'الأسبوع 12 | تاريخ متعدد المراكز: تبادل وحركة وحدود','subtitle':'لا عاصمة واحدة ولا قصة صعود/سقوط واحدة تكفيان لتاريخ واسع','type':'quote','quote':'«الخريطة الجيدة لا تقول فقط: انتقل الشيء؛ بل تسأل: ماذا تحرك، عبر من، وبأي دليل، وما الذي تغيّر؟»','prompt':'المعرض يبرهن دعوى محدودة، ولا يثبت تفوقاً أو حكماً حضارياً شاملاً.'},
 {'title':'المركز أكثر من مكان','type':'two','left_title':'قد يكون مركزاً','left':['مدينة أو إقليماً','شبكة علم أو تجارة','راعية أو مؤسسة','طريقاً أو لغة'], 'right_title':'ولا يعني الطرف','right':['الهامشية المطلقة','غياب الفاعلية','تبعية بلا سؤال']},
 {'title':'سلسلة انتقال المعرفة','type':'steps','steps':['شيء','مركزان','وسيط','مصدر','قراءة','حد'],'note':'لا تستعمل سهم «انتقال» عندما يكون الدليل مجرد تزامن أو تشابه.'},
 {'title':'مادة الأسبوع | تعدد المراكز','subtitle':'100 سؤال 5–8 و32–34 | السجل M3-S15A إلى M3-S18','bullets':['اختاروا مقتطفاً واحداً مراجَعاً قبل اللقاء، لا سلسلة ادعاءات واسعة.','حلقتا 32–33 أصل مناسب لخريطة مراكز؛ الحلقة 34 محجوزة لمراجعة حساسية إضافية.','المطلوب: حركة معرفة/أشخاص/مواد مع مصدر وحد، لا قصة حضارية كلية.'], 'size':17},
 {'title':'نشاط B6 | معرض تاريخي صغير','bullets':['لوحة واحدة: الشيء المتحرك + مركزان + وسيط + مصدر + حد.','يكتب الزائر سؤال مصدر وتعليق إنصاف، لا حكماً على جماعة.','راجعوا الأفعال: «يثبت»، «يرجح»، «يوحي»، «لا نعرف».','احذفوا كل جملة لا يمكن ربطها بدليل أو سؤال محدد.'], 'size':18},
 {'title':'مذكرة الحالة النهائية','type':'steps','steps':['سؤال','خط زمني','مصدر','دعوى','بديل','حد'],'note':'درس حياتي محدود: مهارة تحقق أو إنصاف، لا وصفة سياسية أو حكم هوية.'},
 {'title':'ما الذي سنحمله معنا؟','type':'two','left_title':'مهارة','left':['مصدر ونطاق وحد','قراءة بديلة منصفة','خريطة لا تختزل'], 'right_title':'عادة','right':['توقف قبل المشاركة','اسأل عن الموضع','افصل التاريخ عن الاستقطاب']},
 {'title':'القياس الختامي وبوابة المراجعة','bullets':['مهمة بعدية 0–8: طبقات، نطاق، بديل، وحد.','استبيان: الوضوح، الأمان، العبء، والاستعمال بعد 7–10 أيام.','أي إشارة أمان حمراء تسبق مكسب التعلم؛ توقفوا وراجعوا الحالة.','ما الخطوة التي سأستعملها قبل مشاركة رواية تاريخية؟'], 'size':18},
]

# DOCX
make_docx('01_facilitator_guide_module_03.md', '01_facilitator_guide_module_03.docx', 'دليل الميسر', 'الوحدة 3: السلطة والخلاف والانتماء في التاريخ المبكر')
make_docx('02_learner_workbook_module_03.md', '02_learner_workbook_module_03.docx', 'دفتر المتعلم', 'الوحدة 3: السلطة والخلاف والانتماء في التاريخ المبكر')
make_docx('03_activity_cards_module_03.md', '03_activity_cards_module_03.docx', 'بطاقات الأنشطة', 'الوحدة 3: السلطة والخلاف والانتماء في التاريخ المبكر')
make_docx('06_release_gate_and_revision_note.md', '06_release_gate_and_revision_note.docx', 'بوابة الإصدار والمراجعة', 'الوحدة 3: السلطة والخلاف والانتماء في التاريخ المبكر')
make_docx('07_pilot_protocol_module_03.md', '07_pilot_protocol_module_03.docx', 'بروتوكول تجربة Pilot', 'الوحدة 3: السلطة والخلاف والانتماء في التاريخ المبكر')

# XLSX
csv_to_xlsx('04_resource_registry_v0_1.csv', '04_resource_registry_v0_1.xlsx', 'سجل الموارد')
csv_to_xlsx('05_glossary_v0_1.csv', '05_glossary_v0_1.xlsx', 'المعجم')
csv_to_xlsx('08_pilot_data_template.csv', '08_pilot_data_template.xlsx', 'Pilot data')

# PPTX
slide_deck(9, '01_week_9_fitna_time_narrative_memory.pptx', week9)
slide_deck(10, '02_week_10_authority_claim_not_personalization.pptx', week10)
slide_deck(11, '03_week_11_systems_power_knowledge_conflict.pptx', week11)
slide_deck(12, '04_week_12_multiple_centres_exchange_boundaries.pptx', week12)

# Package only publishable deliverables and reproducible sources.
all_files = list(OUT.glob('*.docx')) + list(OUT.glob('*.xlsx')) + list(SLIDES.glob('*.pptx'))
for path in all_files:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert '[Content_Types].xml' in names, f'Invalid OOXML: {path}'
        if path.suffix == '.docx': assert 'word/document.xml' in names
        if path.suffix == '.xlsx': assert 'xl/workbook.xml' in names
        if path.suffix == '.pptx': assert 'ppt/presentation.xml' in names

zip_path = ROOT / 'module_03_production_pack_v0_1.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file(): z.write(path, arcname=f'module_03_production_pack_v0_1/{path.relative_to(OUT)}')
    for name in ['README.md','01_facilitator_guide_module_03.md','02_learner_workbook_module_03.md','03_activity_cards_module_03.md','04_resource_registry_v0_1.csv','05_glossary_v0_1.csv','06_release_gate_and_revision_note.md','07_pilot_protocol_module_03.md','08_pilot_data_template.csv','09_validation_report_v0_1.md','create_module_03_ooxml.py']:
        z.write(ROOT / name, arcname=f'module_03_production_pack_v0_1/source/{name}')
with zipfile.ZipFile(zip_path) as z: assert z.testzip() is None
print('Created and validated:')
for path in all_files: print(path.relative_to(ROOT), path.stat().st_size)
print(zip_path.relative_to(ROOT), zip_path.stat().st_size)
