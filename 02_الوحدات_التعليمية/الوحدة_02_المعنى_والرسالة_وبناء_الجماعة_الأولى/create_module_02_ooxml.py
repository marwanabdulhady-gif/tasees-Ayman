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

ROOT = Path('/home/user/module_02_meaning_message_community')
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
    set_rtl(hp); rr = hp.add_run('من اليقين إلى الوعي والعمل — الوحدة 2'); set_run_font(rr, 8.5, TEAL)
    fp = sec.footer.paragraphs[0]
    set_rtl(fp); rr = fp.add_run('مسودة إنتاجية v0.1 — 22 أكتوبر 2026'); set_run_font(rr, 8, MUTED)
    # cover
    p = doc.add_paragraph(); set_rtl(p)
    p.paragraph_format.space_before = Pt(90)
    r = p.add_run(title); set_run_font(r, 27, NAVY); r.bold = True
    p2 = doc.add_paragraph(); set_rtl(p2)
    r = p2.add_run(subtitle); set_run_font(r, 15, TEAL)
    p3 = doc.add_paragraph(); set_rtl(p3)
    r = p3.add_run('مسودة إنتاجية v0.1 | العربية | 22 أكتوبر 2026'); set_run_font(r, 10.5, MUTED)
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
    add_textbox(slide, Inches(.55), Inches(7.12), Inches(12.25), Inches(.22), f'الوحدة 2 — المعنى والرسالة وبناء الجماعة الأولى | الأسبوع {week} | مسودة إنتاجية v0.1', 7.5, MUTED)

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


week5 = [
 {'title':'الأسبوع 5 | المعنى والاختيار والمسؤولية','subtitle':'ليس كل سؤال مهماً يطلب النوع نفسه من الدليل','type':'quote','quote':'«حين أسأل: لماذا أعيش؟ ما الذي يستطيع الوصف أن يبينه، وما الذي يحتاج معنى وقيمة والتزاماً؟»','prompt':'من حقك أن تسأل، ومن حقك أن تمرّ. لا نطلب إعلان معتقد أو تجربة شخصية.'},
 {'title':'ما الذي سنتعلمه اليوم؟','type':'two','left_title':'مهارة','left':['تمييز الوصف من التفسير والقيمة','تسمية افتراض في السؤال','اختيار دليل أو حوار مناسب'], 'right_title':'أثر مسؤول','right':['قرار صغير لا شعار كبير','إفساح مساحة للاختلاف','تجنب اليقين المتعجل أو لوم الذات']},
 {'title':'أربعة أنواع من الكلام','type':'steps','steps':['وصف','تفسير','قيمة','معنى/التزام'],'note':'قد تجتمع الطبقات في جملة واحدة؛ مهمتنا فصلها قبل النقاش.'},
 {'title':'حدود مفيدة لا حواجز','type':'two','left_title':'يساعدنا الوصف','left':['كيف يحدث أمر ما؟','ما الأنماط والنتائج؟','ما الذي يظهره الدليل المتاح؟'], 'right_title':'ويحتاج المعنى أيضاً','right':['ما الغاية أو القيمة؟','ما الالتزام الذي أختاره؟','كيف أعيش مع عدم اليقين؟']},
 {'title':'مادة الأسبوع | اقرأ بوصفها دعوى','subtitle':'رحلة اليقين 8 و9 — مواضع في السجل M2-S01 وM2-S02','bullets':['المصدر يقدّم إطاراً إيمانياً/فلسفياً عن الغاية والاختيار.','لا نجعله برهاناً تجريبياً على كل نتيجة نفسية أو عصبية.','اسأل: ما الدعوى؟ ما الدليل المذكور؟ ما الافتراض؟ ما اعتراض منصف؟','لا نستخدم حلقات التطور/الجينات المحجوزة في هذه النسخة.'], 'size':17},
 {'title':'نشاط B1 | بوصلة المعنى','type':'steps','steps':['سؤال','افتراض','نوع دليل','معنى/قيمة','ممارسة صغيرة'],'note':'ابدأوا بحالة سارة الافتراضية أو مثال لا يكشف خصوصيتكم.'},
 {'title':'من معنى إلى ممارسة عادلة','bullets':['اختر قيمة واحدة: أمانة، رحمة، شجاعة، عدل…','صمّم فعلاً صغيراً خلال 7 أيام يمكن ملاحظته بلا مراقبة للآخرين.','توقع عائقاً واحداً وضع خطة بديلة.','النجاح: خطوة واعية، لا كمال ولا شهادة هوية.'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['جملة دقيقة: «أستطيع أن أقول… أما قول… فيحتاج…».','سؤال بقي مفتوحاً: __________________.','وضوح اللقاء من 1–5؛ هل كان وقت التحضير مناسباً؟','سجل أي قلق لغوي/شعوري للميسر بلا اسم إذا أردت.'], 'size':19},
]
week6 = [
 {'title':'الأسبوع 6 | الرسالة والسيرة: خريطة الدليل','subtitle':'احترام النص لا يمنع سؤال المصدر؛ وسؤال المصدر لا يساوي ازدراء النص','type':'quote','quote':'«ما الذي يقوله المصدر مباشرة؟ وما الذي أضفته أنا كتفسير أو حكم؟»','prompt':'الهدف: دقة وإنصاف، لا نتيجة معدّة سلفاً.'},
 {'title':'خريطة الدليل في خمس خانات','type':'steps','steps':['الدعوى','نوع المصدر','دليل مباشر','تفسير/افتراض','حد وثقة'],'note':'درجة الثقة وصف مؤقت للدليل، لا مقياس إيمان أو ولاء.'},
 {'title':'المصدر لا يعمل وحده','type':'two','left_title':'اسأل عن','left':['القرب والناقل والغرض','اللغة والجمهور والسياق','ما الذي يحضر وما يغيب'], 'right_title':'ولا تفترض','right':['القرب = صدق كامل','التأخر = لا قيمة','النص المعياري = جواب تاريخي آلي']},
 {'title':'وظيفتان يمكن أن تتداخلا','type':'two','left_title':'للمؤمن/التقليد','left':['نص معياري وهداية والتزام','قراءة داخل أفق اعتقادي'], 'right_title':'للباحث التاريخي','right':['مادة عن الماضي وتلقيه','أسئلة زمن/نقل/مقارنة/حدود']},
 {'title':'مادة الأسبوع | مصدران حجاجيان','subtitle':'100 سؤال 09 (M2-S05) و10 (M2-S06)','bullets':['الحلقة 09: دعوى عن نقل السيرة وتاريخ التدوين.','الحلقة 10: دعوى مقارنة أديان ذات حساسية عالية.','نحلل البنية والحدود؛ لا ننسب للحلقة إجماعاً تاريخياً أو لاهوتياً.','راجع الفيديو/النص الأصلي قبل أي اقتباس؛ التفريغ آلي.'], 'size':17},
 {'title':'نشاط B2 | خريطة دليل','bullets':['خذوا العبارة: «المصدر المتأخر لا قيمة له تاريخياً».','ما الجزء الذي قد يكون صحيحاً؟ ما القفزة غير المبررة؟','ما المعلومات اللازمة قبل الحكم؟','أضيفوا: مصدر مكمل، اعتراض منصف، ودرجة ثقة مع سبب.'], 'size':18},
 {'title':'ثلاث زوايا لا تتنافس','type':'steps','steps':['ماذا يقول؟','كيف نفحصه؟','ماذا يعني لنا؟'],'note':'لا ننتقل من «قيل في مصدر» إلى «ثبت كل شيء» أو «لا قيمة له».'},
 {'title':'بطاقة الخروج','bullets':['أكثر خانة أحتاج إليها: الدعوى / المصدر / الدليل / التفسير / الحد.','أعد صياغة رأي مخالف بحيث يقبله صاحبه بدرجة 8 من 10.','قيّم الوضوح والأمان والعبء (1–5) واكتب سؤال تحقق واحداً.'], 'size':18},
]
week7 = [
 {'title':'الأسبوع 7 | السؤال الحساس: سياق ومصادر وكرامة','subtitle':'يمكن أن نسأل السؤال الصعب بلا تجريح، وبلا تبرير متعجل','type':'quote','quote':'«السياق يفسر، لكنه لا يعفينا تلقائياً من تسمية المعيار أو من رعاية الكرامة.»','prompt':'لا نطلب من أحد الدفاع عن جماعة أو عن تجربة شخصية. خيار المرور محفوظ.'},
 {'title':'عقد الأمان الخاص باليوم','type':'two','left_title':'نفعل','left':['نستخدم لغة وصفية غير مهينة','نمرّر دورنا إن احتجنا','نكتب السؤال قبل القفز للإجابة','نستعمل حالات افتراضية'], 'right_title':'لا نفعل','right':['لا مناظرة هوية','لا إعادة لعبارات جارحة','لا طلب اعتراف شخصي','لا استنتاجات عامة عن جماعات']},
 {'title':'افصل السؤال قبل الإجابة','type':'steps','steps':['ماذا حدث؟','كيف عرفنا؟','كيف فُهم؟','كيف نقيمه؟'],'note':'الخلط بين سؤالين هو أحد أسباب التصعيد والحكم المتعجل.'},
 {'title':'عدسات السياق الأربع','type':'two','left_title':'مصدر وزمن','left':['من نقل؟ كيف وصل؟','ما الأعراف والبنى والقيود؟'], 'right_title':'معيار وأثر','right':['ما المعيار الذي أصرح به؟','من قد يتأذى من صياغتي؟']},
 {'title':'مادة الأسبوع | للمختبر لا للحسم','subtitle':'100 سؤال 12 و13 — M2-S07 وM2-S08','bullets':['المادتان تقدمان دفاعاً من موقع محدد؛ لا تعرضان تعدد الآراء كاملاً.','نختار حالة افتراضية افتراضياً، لا تفاصيل شخصية أو مثيرة.','لا يبرر السياق الضرر، ولا يلغي التقييم الحاضر الحاجة إلى مصدر.','أي قلق: توقف، اكتب، عد إلى البروتوكول، وأحِل عند الحاجة.'], 'size':16},
 {'title':'نشاط B3 | عدسات السياق','bullets':['حالة: رواية تاريخية يُراد جعلها معياراً مباشراً اليوم.','ضعوا سؤالين لكل عدسة: المصدر، الزمن، المعيار، الأثر.','اكتبوا جملة تمنع «التبرير بالسياق» وجملة تمنع «الإدانة بلا مصدر».'], 'size':18},
 {'title':'نشاط B4 | سجل المعرفة','type':'steps','steps':['نعرف من…','نرجّح…','نختلف حول…','لا نعرف بعد…'],'note':'قول «لا أعرف» خطوة بحثية مسؤولة، لا هروب ولا حكم نهائي.'},
 {'title':'إغلاق آمن','bullets':['اكتب سؤالاً معلّقاً من دون أسماء أو تفاصيل شخصية.','ما المصدر/الخبير الذي نحتاجه؟ من يتابع؟ ومتى؟','قيّم الأمان بصدق؛ أي إشارة أذى توقف استخدام الحالة في النسخة التالية.','لا يعالج هذا اللقاء أزمة نفسية أو فتوى فردية؛ توجد إحالة مناسبة عند الحاجة.'], 'size':17},
]
week8 = [
 {'title':'الأسبوع 8 | من قيمة إلى جماعة قابلة للمراجعة','subtitle':'نتعلم من التاريخ مهارة، لا ننقل منه وصفة سياسية جاهزة','type':'quote','quote':'«القيمة التي لا تصبح ممارسة قد تبقى شعاراً؛ والممارسة التي لا تراجع قد تصبح سيطرة.»','prompt':'هذه الجلسة عن جماعة تعلم صغيرة، لا عن دولة أو حزب أو فرض على الآخرين.'},
 {'title':'الحد التاريخي المهم','type':'two','left_title':'يمكن أن نتعلم','left':['أسئلة عن بناء الثقة والدور','صلة القيم بالممارسة','كيف نقرأ سرداً تاريخياً'], 'right_title':'لا نستنتج مباشرة','right':['خطة حكم معاصرة','شرعنة عنف أو سلطة','تطابقاً بين زمنين مختلفين']},
 {'title':'سلسلة التصميم المسؤول','type':'steps','steps':['قيمة','ممارسة','دور','قاعدة','مراجعة'],'note':'إذا غاب الاعتراض الآمن أو موعد المراجعة، فالميثاق غير مكتمل.'},
 {'title':'مادة الأسبوع | إطاران لا وصفة','subtitle':'100 سؤال 14 (M2-S09) وتأسيس وعي: المحاضرة 1 (M2-S10)','bullets':['خريطة مراحل السيرة في الحلقة إطار سردي واحد لا تقسيم واجب.','سلسلة المعرفة/التوجه/السلوك إطار تربوي لصاحبها لا قانون نفسي مثبت بذاته.','نستخدم الإطارين لصنع ميثاق تعلم عادل ومحدود.'], 'size':18},
 {'title':'نشاط B5 | مختبر الميثاق','bullets':['اختاروا قيمة واحدة لمجموعة قراءة/خدمة لمدة شهر.','صمموا ممارسة أسبوعية منخفضة الكلفة.','حددوا دوراً قابلاً للتدوير، وقاعدة للمصدر أو الحوار.','أضيفوا: اعتراض آمن + موعد مراجعة.'], 'size':18},
 {'title':'نشاط B6 | خريطة الأثر','type':'two','left_title':'اسألوا من يُرى','left':['عضو جديد','عضو هادئ','من لديه وقت أقل'], 'right_title':'واسألوا من قد يُنسى','right':['من خارج المجموعة','من يعترض','من يقع عليه أثر القرار']},
 {'title':'تجربة 7 أيام','bullets':['قيمة واحدة، ممارسة واحدة، وقت/مكان، عائق وخطة بديلة.','شريك مساءلة اختياري، لا مراقبة أو فضح.','راقب أثر الممارسة من دون محاكمة الذات أو الآخرين.','بعد 7–10 أيام: نعم/جزئياً/لا + عائق أو أثر غير مقصود.'], 'size':18},
 {'title':'ختام الوحدة وبوابة المراجعة','bullets':['مهمة بعدية: طبقات الكلام وخريطة الدليل (0–8).','استبيان: الفهم، الأمان، العبء، والأثر الأولي.','أي إشارة أمان حمراء تتقدم على مكسب التعلم.','ما السؤال الذي سأحمله، وما الفعل الصغير الذي سأجربه؟'], 'size':18},
]

# DOCX
make_docx('01_facilitator_guide_module_02.md', '01_facilitator_guide_module_02.docx', 'دليل الميسر', 'الوحدة 2: المعنى والرسالة وبناء الجماعة الأولى')
make_docx('02_learner_workbook_module_02.md', '02_learner_workbook_module_02.docx', 'دفتر المتعلم', 'الوحدة 2: المعنى والرسالة وبناء الجماعة الأولى')
make_docx('03_activity_cards_module_02.md', '03_activity_cards_module_02.docx', 'بطاقات الأنشطة', 'الوحدة 2: المعنى والرسالة وبناء الجماعة الأولى')
make_docx('06_release_gate_and_revision_note.md', '06_release_gate_and_revision_note.docx', 'بوابة الإصدار والمراجعة', 'الوحدة 2: المعنى والرسالة وبناء الجماعة الأولى')
make_docx('07_pilot_protocol_module_02.md', '07_pilot_protocol_module_02.docx', 'بروتوكول تجربة Pilot', 'الوحدة 2: المعنى والرسالة وبناء الجماعة الأولى')

# XLSX
csv_to_xlsx('04_resource_registry_v0_1.csv', '04_resource_registry_v0_1.xlsx', 'سجل الموارد')
csv_to_xlsx('05_glossary_v0_1.csv', '05_glossary_v0_1.xlsx', 'المعجم')
csv_to_xlsx('08_pilot_data_template.csv', '08_pilot_data_template.xlsx', 'Pilot data')

# PPTX
slide_deck(5, '01_week_5_meaning_choice_responsibility.pptx', week5)
slide_deck(6, '02_week_6_message_sira_evidence_map.pptx', week6)
slide_deck(7, '03_week_7_sensitive_questions_context_dignity.pptx', week7)
slide_deck(8, '04_week_8_value_to_reviewable_community.pptx', week8)

# validation
all_files = list(OUT.glob('*.docx')) + list(OUT.glob('*.xlsx')) + list(SLIDES.glob('*.pptx'))
for path in all_files:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert '[Content_Types].xml' in names, f'Invalid OOXML: {path}'
        if path.suffix == '.docx': assert 'word/document.xml' in names
        if path.suffix == '.xlsx': assert 'xl/workbook.xml' in names
        if path.suffix == '.pptx': assert 'ppt/presentation.xml' in names

zip_path = ROOT / 'module_02_production_pack_v0_1.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file():
            z.write(path, arcname=f'module_02_production_pack_v0_1/{path.relative_to(OUT)}')
    for name in ['README.md','01_facilitator_guide_module_02.md','02_learner_workbook_module_02.md','03_activity_cards_module_02.md','04_resource_registry_v0_1.csv','05_glossary_v0_1.csv','06_release_gate_and_revision_note.md','07_pilot_protocol_module_02.md','08_pilot_data_template.csv']:
        z.write(ROOT / name, arcname=f'module_02_production_pack_v0_1/source/{name}')
print('Created and validated:')
for path in all_files:
    print(path.relative_to(ROOT), path.stat().st_size)
print(zip_path.relative_to(ROOT), zip_path.stat().st_size)
