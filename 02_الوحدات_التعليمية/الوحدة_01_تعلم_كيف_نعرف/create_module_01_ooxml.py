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

ROOT = Path('/home/user/module_01_learning_how_to_know')
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
    set_rtl(hp); rr = hp.add_run('من اليقين إلى الوعي والعمل — الوحدة 1'); set_run_font(rr, 8.5, TEAL)
    fp = sec.footer.paragraphs[0]
    set_rtl(fp); rr = fp.add_run('نسخة Pilot v0.1 — 22 أكتوبر 2026'); set_run_font(rr, 8, MUTED)
    # cover
    p = doc.add_paragraph(); set_rtl(p)
    p.paragraph_format.space_before = Pt(90)
    r = p.add_run(title); set_run_font(r, 27, NAVY); r.bold = True
    p2 = doc.add_paragraph(); set_rtl(p2)
    r = p2.add_run(subtitle); set_run_font(r, 15, TEAL)
    p3 = doc.add_paragraph(); set_rtl(p3)
    r = p3.add_run('نسخة Pilot v0.1 | العربية | 22 أكتوبر 2026'); set_run_font(r, 10.5, MUTED)
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
    add_textbox(slide, Inches(.55), Inches(7.12), Inches(12.25), Inches(.22), f'الوحدة 1 — تعلّم كيف نعرف | الأسبوع {week} | نسخة Pilot v0.1', 7.5, MUTED)

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

week1 = [
 {'title':'الأسبوع 1 | من السؤال الشخصي إلى خريطة التعلم','subtitle':'كيف ننتقل من معلومة أو قلق إلى سؤال يستحق التعلم؟','type':'quote','quote':'«كيف أتعامل مع سؤال مهم من غير هلع، ولا سذاجة، ولا يقين متعجل؟»','prompt':'اكتب لنفسك: سؤال واحد تريد أن تفهمه بنهاية الدورة.'},
 {'title':'اتفاق التعلم','subtitle':'نحمي السؤال والإنسان معاً','type':'two','left_title':'نفعل','left':['نسأل عن الفكرة لا عن النيات','نصرح بما لا نعرفه','نلخص قبل أن نعترض','نسجل المصدر والموضع'], 'right_title':'لا نفعل','right':['لا نعمم على مجموعات بشرية','لا نفرض كشف تجربة شخصية','لا نحول السؤال إلى تهمة','لا نعرض مورداً غير مسجل كحقيقة حاسمة']},
 {'title':'خريطة الوحدة','type':'steps','steps':['سؤال','دعوى','دليل','تفسير','حوار','فعل'],'note':'الهدف ليس حفظ المصطلحات؛ الهدف استعمالها في موقف حقيقي.'},
 {'title':'أربع طبقات في التعلم','subtitle':'من المقاطع التمهيدية: معرفة، مهارة، توجه، ووعي','type':'two','left_title':'ما أتعلمه','left':['معلومة: شيء أعرفه','مهارة: شيء أقدر أن أفعله','توجه: استعداد أو قيمة تحركني'], 'right_title':'ما نريده','right':['وعي: معرفة تصحبها مسؤولية','لا تتحول المعرفة تلقائياً إلى فعل','نبحث عن عادات صغيرة قابلة للاستمرار']},
 {'title':'مختبر المصدر الأولي','subtitle':'المقاطع الثلاثة مادة لطرح الأسئلة، لا أجوبة نهائية','bullets':['تأسيس وعي — المحاضرة 1: المعرفة/المهارة/التوجه','100 سؤال — الحلقة 1: سؤال التاريخ والذاكرة','رحلة اليقين — الحلقة 1: بناء الدعائم والأسئلة المؤسسة','اسأل: ما السؤال؟ ما الدعوى؟ ما الذي لا يثبته المقطع وحده؟'], 'size':17},
 {'title':'نشاط A1 | خريطة السؤال','subtitle':'فردي 6 دقائق، ثم ثنائي 8 دقائق','bullets':['اكتب السؤال كما جاءك أولاً.','ضع دائرة حول الكلمات العامة أو الحادة: كل، دائماً، واضح…','أعد صياغته: موضوع محدد + سياق + نوع معرفة مطلوب.','اطلب من شريكك أن يسأل: ما الذي يحتاج تعريفاً أولاً؟'], 'size':18},
 {'title':'من المعلومة إلى الفعل','type':'quote','quote':'«ما معلومة صحيحة أعرفها، لكنها لم تغيّر سلوكي؟ وما الذي كان ينقصها؟»','prompt':'في ثلاثيات: ناقشوا مهارة أو بيئة أو دافعاً يمكن أن يحوّل المعرفة إلى ممارسة.'},
 {'title':'بطاقة الخروج وتجربة الأسبوع','bullets':['بطاقة الخروج: سؤال أريد تعلمه + عادة واحدة سأجربها.','تجربة 24 ساعة: قبل مشاركة خبر أو مقطع، دوّن المصدر ونوع الدعوى وما لا تعرفه بعد.','لا تشارك نتيجة تدريبك لإحراج أحد؛ الهدف بناء عادة تحقق.'], 'size':18},
]
week2 = [
 {'title':'الأسبوع 2 | الدليل والرواية والتفسير','subtitle':'عندما أسمع دعوى كبيرة، ماذا أفحص قبل قبولها أو رفضها؟','type':'quote','quote':'«المصدر ليس الحقيقة نفسها؛ إنه نافذة لها زاوية وسياق وحدود.»','prompt':'فكر في رواية سمعتها مؤخراً: ما أقوى مصدر لها؟'},
 {'title':'استرجاع سريع','bullets':['ارفع بطاقتك: واقعة، رواية، تفسير، أم حكم؟','لا يكفي التصنيف وحده: اسأل ما الدليل المناسب لكل جملة.','تذكر: وجود سؤال أو اعتراض لا يثبت النتيجة التي يفضّلها صاحبه.'], 'size':19},
 {'title':'خريطة الفحص الأولي','type':'steps','steps':['الدعوى','المصدر','السياق','المقارنة','درجة الثقة'],'note':'لا يوجد ترتيب ميكانيكي للمصادر؛ توجد أسئلة أفضل.'},
 {'title':'مصدر أولي ≠ حقيقة نهائية','type':'two','left_title':'قد يفيد في','left':['قربه من الحدث','لغة الفاعلين وتصوراتهم','تفاصيل لا تظهر لاحقاً'], 'right_title':'لكن قد يحده','right':['الغرض والمصلحة','المعرفة الجزئية','الذاكرة أو الرقابة','ما لا يستطيع صاحبه رؤيته']},
 {'title':'مادة الأسبوع من 100 سؤال','subtitle':'نقرأ لاستخراج بنية الادعاء، لا لتبني التعميم','bullets':['الحلقة 2 (01:15–07:18): دعوى «التاريخ يكتبه المنتصر» — ما نطاقها؟','الحلقة 3 (02:05–10:26): التمييز بين جمع المعلومات وتفسيرها.','الحلقة 3 (25:05–35:38): اختبار الاتساق الزمني مثالاً.','المطلوب: سجل الموضع، ثم اكتب ما الذي يحتاجه الادعاء كي يثبت.'], 'size':16},
 {'title':'نشاط A3 | سلم المصدر','bullets':['رتبوا: رسالة معاصرة، بيان رسمي، مذكرات متأخرة، دراسة موثقة، فيديو بلا مصادر.','لا تسألوا: أيها صحيح؟ اسألوا: أي سؤال يمكن أن يخدمه كل منها؟','أضيفوا: ما المصدر الناقص الذي تتمنون العثور عليه؟'], 'size':18},
 {'title':'نشاط A4 | محكمة الادعاء','subtitle':'الأدوار: صاحب الدعوى، باحث المصدر، ناقد بديل التفسير، مقيّم الثقة، مقرر','type':'steps','steps':['قل الدعوى','اطلب الموضع','افحص الحد','اعرض بديلاً','حدّد الثقة'],'note':'ينجح النشاط حين تصبح الدعوى أدق، لا حين ينتصر طرف.'},
 {'title':'بطاقة الخروج','bullets':['اكتب: دعوى واحدة، أقوى مصدر وجدته، وما الذي بقي مجهولاً.','اختر درجة ثقة 0–4، واكتب سبب الدرجة.','تجربة الحياة: ابنِ بطاقة مصدر لدعوى متداولة، من دون نشرها أو إحراج ناقلها.'], 'size':18},
]
week3 = [
 {'title':'الأسبوع 3 | الفكرة والعادة والبيئة','subtitle':'كيف تتحول فكرة صغيرة إلى نمط سلوكي أو اجتماعي؟','type':'quote','quote':'«لا تسأل فقط: هل الفكرة صحيحة؟ اسأل أيضاً: ماذا تفعل باللغة والانتباه والعاطفة والسلوك؟»','prompt':'تذكر عنواناً أو مقطعاً غيّر شعورك بسرعة.'},
 {'title':'عنوانان، حدث واحد','subtitle':'نشاط افتتاحي: لا نسأل أولاً أيهما صحيح؛ نسأل ماذا يدعو كل عنوان أن نشعر ونفعل.','bullets':['ما الكلمة المشحونة؟','ما الافتراض الذي تقترحه؟','ما الفاعل الذي تخفيه أو تبرزه؟','ما مصدر أو سياق قد يغير قراءتك؟'], 'size':19},
 {'title':'من المدخل إلى العادة','type':'steps','steps':['مدخل','افتراض','شعور','فعل','مكافأة','عادة'],'note':'التدخل الأفضل صغير وواقعي، وليس لوماً للذات أو للآخرين.'},
 {'title':'لا تخلط أنواع الادعاء','type':'two','left_title':'أمثلة أنواع','left':['ادعاء علمي: يحتاج بيانات ومنهج','توصيف تاريخي: يحتاج مصادر وموضعاً','حكم أخلاقي: يحتاج قيماً ووقائع'], 'right_title':'احذر الخلط','right':['البيانات لا تحسم وحدها معنى فلسفياً','التفسير ليس واقعة','الانحياز لا يلغي المصدر تلقائياً']},
 {'title':'مادة الأسبوع','bullets':['تأسيس وعي — المحاضرة 1: من المعرفة إلى توجه وعادة.','رحلة اليقين 20: كيف نفكر؟ استخدمها لفحص نوع الادعاء والمنهج.','100 سؤال 3 (35:38–48:04): التعامل مع سؤال أو دعوى قبل القفز لنتيجة.','التزم بالموضع الدقيق؛ لا تنسب اقتباساً غير راجعتَه.'], 'size':17},
 {'title':'نشاط A5 | تشريح عادة معرفية','bullets':['الحالة: عنوان مثير → غضب → إعادة إرسال → إعجاب المجموعة → عادة.','ارسم: مدخل / افتراض / شعور / فعل / مكافأة.','ضع نقطة تدخل واحدة: تأخير 5 دقائق، أو مصدر أصلي، أو سؤال لشخص موثوق.'], 'size':18},
 {'title':'صمّم تجربة 7 أيام','bullets':['اختر عادة واحدة فقط: التوقف قبل المشاركة، الوصول للأصل، تدوين الثقة، أو سؤال مختلف بإنصاف.','حدد الإشارة: متى وأين ستتذكر التجربة؟','حدد دليل الإنجاز: ماذا ستدوّن؟','لا تقيس النجاح بأنك لم تخطئ أبداً؛ قسه بوجود خطوة تحقق.'], 'size':17},
 {'title':'بطاقة الخروج','bullets':['ما العبارة التي تحتاج سياقاً قبل أن أصنفها؟','ما نقطة التدخل الواقعية في عادتي المعرفية؟','كيف سأقيس التجربة من دون مراقبة الآخرين أو لومهم؟'], 'size':19},
]
week4 = [
 {'title':'الأسبوع 4 | الحوار المنصف والفعل المسؤول','subtitle':'كيف نختلف ونتعلم في الوقت نفسه؟','type':'quote','quote':'«لا يبدأ النقد الجيد قبل أن يستطيع صاحبه أن يقول: نعم، لقد فهمت موقفي.»','prompt':'اكتب رأياً تختلف معه، ثم اكتب أقوى صياغة منصفة له.'},
 {'title':'بروتوكول الحوار','type':'steps','steps':['قل الدعوى','اسأل','لخّص','اتفق/اختلف','تحقق','اختم بخطوة'],'note':'الحوار ليس مسابقة سرعة؛ إنه بنية لحماية الفهم والكرامة.'},
 {'title':'قبل أن تعترض','type':'two','left_title':'افعل','left':['اطلب تعريفاً أو موضعاً','لخص حتى ينال 8/10 في الإنصاف','ميّز الواقعة من التفسير والحكم','أعلن حدود علمك'], 'right_title':'تجنب','right':['نسب النيات','الرد على نسخة ضعيفة من الرأي','التعميم على جماعات','تحويل عدم المعرفة إلى يقين']},
 {'title':'نشاط A7 | تبديل الموقع','bullets':['طرف أول يشرح رأيه في دقيقتين.','طرف ثانٍ يلخصه بلا تعليق.','صاحب الرأي يمنح درجة إنصاف من 1 إلى 10.','لا يبدأ النقد قبل 8/10 على الأقل.','مراقب يرصد: سؤال توضيحي، حد معرفي، فصل الفكرة عن الشخص.'], 'size':17},
 {'title':'نشاط A8 | مجلس الأدلة','subtitle':'حالة مركبة: رواية تاريخية + خبر معاصر + أثر شخصي','bullets':['الأدوار: ميسر، صاحب رواية، موثق مصادر، ناقد تفسير، مراقب لغة، مقرر.','المخرج: قابل للدعم الآن / محتمل غير محسوم / يلزم بحثه.','المعيار: الوضوح والإنصاف ودقة الخطوة التالية؛ لا الانتصار.'], 'size':18},
 {'title':'قياس نهاية الوحدة','bullets':['مهمة تطبيق: صنّف طبقات الكلام، واسأل عن مصدر، وحدد درجة ثقة.','استبيان: وضوح، عبء، أمان، احترام، وأثر أولي.','ملاحظة الحوار: لا ترتب الناس علناً؛ استخدم المتوسط لتحسين التصميم.'], 'size':18},
 {'title':'مشروع 30 يوماً','bullets':['اختر عادة أو تطبيقاً واحداً: نظام تحقق، نادي قراءة، مقابلة ذاكرة محلية، أو درس مصغر.','ضع خطوة أسبوعية ودليل إنجاز ومساعداً إن احتجت.','احم الخصوصية؛ لا تجمع قصص الناس ولا تنشرها بلا إذن.'], 'size':18},
 {'title':'الإغلاق','type':'quote','quote':'«سؤال بقي معي — مهارة اكتسبتها — فعل سأستمر به»','prompt':'املأ بطاقة الخروج، ثم أكمل استبيان الـPilot المجهّل. شكراً لأنك تساعد في بناء بقية الدورة.'},
]

# Build files
make_docx('01_facilitator_guide_module_01.md', '01_facilitator_guide_module_01.docx', 'دليل الميسر', 'الوحدة 1: تعلّم كيف نعرف')
make_docx('02_learner_workbook_module_01.md', '02_learner_workbook_module_01.docx', 'دفتر المتعلم', 'الوحدة 1: تعلّم كيف نعرف')
make_docx('03_activity_cards_module_01.md', '03_activity_cards_module_01.docx', 'بطاقات الأنشطة', 'الوحدة 1: تعلّم كيف نعرف')
make_docx('04_pilot_protocol_module_01.md', '04_pilot_protocol_module_01.docx', 'بروتوكول تجربة Pilot', 'الوحدة 1: تعلّم كيف نعرف')

csv_to_xlsx('05_resource_registry_v0_1.csv', '05_resource_registry_v0_1.xlsx', 'Resource Registry')
csv_to_xlsx('06_glossary_v0_1.csv', '06_glossary_v0_1.xlsx', 'Glossary')
csv_to_xlsx('07_pilot_data_template.csv', '07_pilot_data_template.xlsx', 'Pilot Data')

slide_deck(1, '01_week_1_question_to_learning_map.pptx', week1)
slide_deck(2, '02_week_2_evidence_narrative_interpretation.pptx', week2)
slide_deck(3, '03_week_3_ideas_habits_and_context.pptx', week3)
slide_deck(4, '04_week_4_dialogue_and_responsible_action.pptx', week4)

# Validation (OOXML files are zip packages with required members)
all_files = list(OUT.glob('*.docx')) + list(OUT.glob('*.xlsx')) + list(SLIDES.glob('*.pptx'))
for path in all_files:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert '[Content_Types].xml' in names, f'Invalid OOXML: {path}'
        if path.suffix == '.docx': assert 'word/document.xml' in names
        if path.suffix == '.xlsx': assert 'xl/workbook.xml' in names
        if path.suffix == '.pptx': assert 'ppt/presentation.xml' in names

# Produce a delivery zip, excluding this generator and source markdown/CSV.
zip_path = ROOT / 'module_01_pilot_pack_v0_1.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file():
            z.write(path, arcname=f'module_01_pilot_pack_v0_1/{path.relative_to(OUT)}')
    for name in ['README.md','01_facilitator_guide_module_01.md','02_learner_workbook_module_01.md','03_activity_cards_module_01.md','04_pilot_protocol_module_01.md','05_resource_registry_v0_1.csv','06_glossary_v0_1.csv','07_pilot_data_template.csv']:
        z.write(ROOT / name, arcname=f'module_01_pilot_pack_v0_1/source/{name}')

print('Created and validated:')
for path in all_files:
    print(path.relative_to(ROOT), path.stat().st_size)
print(zip_path.relative_to(ROOT), zip_path.stat().st_size)
