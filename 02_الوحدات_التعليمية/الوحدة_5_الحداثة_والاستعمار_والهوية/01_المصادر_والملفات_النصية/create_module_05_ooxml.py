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

ROOT = Path('/home/user/module_05_modernity_colonialism_identity')
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
    set_rtl(hp); rr = hp.add_run('من اليقين إلى الوعي والعمل — الوحدة 5'); set_run_font(rr, 8.5, TEAL)
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
    add_textbox(slide, Inches(.55), Inches(7.12), Inches(12.25), Inches(.22), f'الوحدة 5 — الحداثة والاستعمار والهوية | الأسبوع {week} | مسودة إنتاجية v0.1', 7.5, MUTED)

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


# ---------------- Deck content: Module 5 ----------------
week17 = [
 {'title':'الأسبوع 17 | احتلال، استعمار، وهيمنة','subtitle':'المصطلح والوثيقة قبل الشعار والتعميم','type':'quote','quote':'«الكلمة الكبيرة بداية سؤال: من يتكلم؟ عن أي زمن ومكان؟ وبأي معيار ودليل؟»','prompt':'لا نطلب موقف هوية. ندرس مصدرًا ونطاقًا، مع حفظ كرامة كل إنسان.'},
 {'title':'مهارة اليوم وأثرها','type':'two','left_title':'مهارة مصدرية','left':['تعريف عملي للمصطلح','قراءة المنشئ والغرض والجمهور','رؤية الغياب وتفاوت القوة'], 'right_title':'أثر مسؤول','right':['لا تعميم على شعب أو دين','لا وثيقة = كل الحقيقة','لا شعار = تفسير']},
 {'title':'مصطلحات لا تتطابق','type':'steps','steps':['احتلال','استعمار','إمبراطورية','هيمنة','استقلال'],'note':'قد تتقاطع في حالة ما؛ لا تستبدل دراسة الحالة بالتعريف العام.'},
 {'title':'الوثيقة ليست مرآة شفافة','type':'two','left_title':'اسأل عن','left':['المنشئ والتاريخ','الغرض والجمهور','اللغة والأرشيف'], 'right_title':'وابحث عن','right':['المصدر المكمل','الصوت الغائب','ما لا تثبته وحدها']},
 {'title':'مادة الأسبوع | عدسة لا قاموس','subtitle':'100 سؤال 50–53 | السجل M5-S01 إلى M5-S04','bullets':['الحلقة 50 مدخل لتعريفات أولية، لا قاموس قانوني أو تاريخي نهائي.','الحلقة 52 ذات عنوان واسع: نحلل آليات ونطاقاً ولا نقرر مؤامرة كلية.','لا نعرض مادة أو وثيقة قبل مراجعة موضعها ومنشئها وسياقها.'], 'size':18},
 {'title':'نشاط E1 | بطاقة المصطلح الحي','type':'steps','steps':['اختر اللفظ','عرّفه','ضع النطاق','سمِّ معيارك','اذكر الحد'],'note':'لا تستعمل اللفظ في مناظرة قبل اكتمال البطاقة.'},
 {'title':'نشاط E2 | وثيقتان، قوة وغياب','bullets':['الميسر يختار وثيقتين قصيرتين موثقتين بعد تحقق.','حللوا المنشئ والغرض والجمهور واللغة والغياب.','اختلاف المنظور لا يلغي تفاوت القوة أو الإكراه.','قولوا: «تظهر الوثيقة ___؛ ولا تثبت وحدها ___.»'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['مصطلح أحتاج إلى تضييقه: ____________.','سؤال سأطرحه عن أي وثيقة: ____________.','صوت/عامل قد يغيب عن المصدر: ____________.','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week18 = [
 {'title':'الأسبوع 18 | الدولة الحديثة والمؤسسات','subtitle':'ما الذي تبنيه المؤسسة وتكافئه وتضعفه؟','type':'quote','quote':'«المؤسسة ليست شخصاً؛ إنها قواعد وأدوار وموارد وحوافز وآثار مقصودة وغير مقصودة.»','prompt':'نحلل مؤسسة قريبة بأمان، لا نُصدر حكماً على دولة أو جهة حاضرة.'},
 {'title':'من ملاحظة إلى سؤال أفضل','type':'steps','steps':['قاعدة','حافز','ممارسة','أثر','حد'],'note':'لا تقفز من ملاحظة واحدة إلى تشخيص شامل أو توصية سياسية.'},
 {'title':'ما الذي نسأل عنه؟','type':'two','left_title':'داخل المؤسسة','left':['قواعد ووقت وموارد','أدوار وتقييم ومكافأة','معرفة محلية وخبرة'], 'right_title':'خارجها','right':['سياق وتفاوت فرص','فئات متأثرة','أثر غير مقصود']},
 {'title':'مادة الأسبوع | حالة وإطار','subtitle':'100 سؤال 54–57 + تأسيس وعي 3–4 | M5-S05 إلى M5-S08 وM5-S20–S21','bullets':['العناوين الثنائية ليست حكماً نهائياً: نفككها إلى سياسات ومؤسسات وآثار.','مواد أيمن تقدم عدسة صاحبها عن المجتمع/الشبكات؛ لا نظرية حاسمة.','لا تعمم حالة تاريخية إلى كل دولة حديثة أو إلى مؤسسات المشاركين.'], 'size':17},
 {'title':'نشاط E3 | خريطة مؤسسة','type':'steps','steps':['قاعدة','مورد','حافز','سلوك','أثر','سؤال'],'note':'ضعوا دالاً للملاحظة المدعومة وفاءً للافتراض. لا تسمّوا أشخاصاً أو جهات حاضرة.'},
 {'title':'أثر غير مقصود','type':'two','left_title':'يمكن أن يساعد','left':['قاعدة واضحة','وقت كافٍ','تغذية راجعة عادلة'], 'right_title':'وقد يضعف','right':['صوتاً هادئاً','وقتاً محدوداً','دافعاً للتعلم العميق']},
 {'title':'ثلاثة مستويات للكتابة','bullets':['ملاحظة: ماذا أرى أو أعرف؟','تفسير: ما الآلية المحتملة؟','توصية/سؤال متابعة: ما الخطوة الصغيرة الآمنة؟','لا تعامل التفسير كأنه ملاحظة، ولا التوصية كأنها حقيقة.'], 'size':19},
 {'title':'بطاقة الخروج','bullets':['ملاحظة محددة: ____________.','تفسير محتمل وحدّه: ____________.','سؤال متابعة أو تحسين صغير غير سياسي: ____________.','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week19 = [
 {'title':'الأسبوع 19 | الحدود وفلسطين والعلمانية','subtitle':'خط زمني محدود، مصادر واضحة، وكرامة لا تفاوض عليها','type':'quote','quote':'«يمكن أن نختلف حول التفسير؛ لا نجعل إنسانية المدنيين أو كرامتهم موضوع مناظرة.»','prompt':'حق المرور محفوظ. لا هوية مطلوبة، ولا اختبار ولاء، ولا توجيه سياسي أو قانوني.'},
 {'title':'افصل طبقات السؤال','type':'steps','steps':['واقعة/وثيقة','تفسير','حكم','توصية'],'note':'عدم خلط الطبقات يجعل الحوار أهدأ وأدق، ولا يطلب من أحد التنازل عن كرامته.'},
 {'title':'الخط الزمني ليس القضية كلها','type':'two','left_title':'يبين','left':['تسلسلاً محدوداً','وثيقة أو مصدرًا','تغير لفظ/مؤسسة'], 'right_title':'ولا يحل','right':['كل التفسير','كل الحقائق','كل الخلاف الحي']},
 {'title':'مصطلح متعدد المعاني','type':'two','left_title':'«الحدود»','left':['ترتيب قانوني/سياسي','خريطة وممارسة','أثر على حياة الناس'], 'right_title':'«العلمانية»','right':['علاقات دين/دولة/قانون','سياقات متعددة','ليست مدحاً أو شتيمة']},
 {'title':'مادة الأسبوع | حالة شديدة الحساسية','subtitle':'100 سؤال 58–64 | M5-S09 إلى M5-S15','bullets':['اختروا دعوى واحدة أو حدثاً واحداً ومصدرًا موثقاً، لا «كل القضية».','الحلقة 62 محجوزة لمقتطف موثق وبروتوكول كرامة، أو تستبدل بحالة مغلقة.','مورد M5-R04 منظور فلسطيني معلن التموضع؛ يُقرأ بوضوح لا كصوت وحيد.'], 'size':17},
 {'title':'نشاط E5 | خط زمني بخمس بطاقات','type':'steps','steps':['زمن','واقعة/وثيقة','مصدر','تفسير','سؤال'],'note':'كل بطاقة تحتاج موضعاً؛ لا صور أو خرائط مجهولة المنشأ.'},
 {'title':'نشاط E6 | خريطة ادعاء حساس','bullets':['منشأ المصدر؟ ما غرضه؟ ما النطاق؟','من يظهر ومن يغيب؟ ما أثر الترجمة أو اللفظ؟','ما الواقعة؟ ما التفسير؟ ما الحكم المنفصل؟','المخرج: دعوى محدودة، مصدر، حد، وخطوة تعلم لاحقة.'], 'size':18},
 {'title':'إغلاق آمن','bullets':['ما أستطيع قوله من مصدر محدد: ____________.','ما لا أستطيع حسمه بعد: ____________.','ما السؤال الذي يحتاج مصدراً/مختصاً لاحقاً: ____________.','قيّم الأمان بصدق؛ أي إشارة أذى توقف استخدام الحالة.'], 'size':18},
]
week20 = [
 {'title':'الأسبوع 20 | الهوية والتماسك اليوم','subtitle':'عادة تواصل صغيرة وحلقة تعلم: فعل مدني لا تعبئة','type':'quote','quote':'«التماسك لا يعني التشابه أو إسكات الاعتراض؛ بل علاقة كرامة ومصدر وحوار يمكن مراجعته.»','prompt':'لا مراقبة للآخرين، لا تعبئة، لا خصومة؛ المشاركة اختيارية وخطوة الأسبوع منخفضة المخاطر.'},
 {'title':'هوية وانتماء وتماسك','type':'steps','steps':['هوية','انتماء','شبكة','مؤسسة وسيطة','عادة','مراجعة'],'note':'كل مفهوم متعدد ومتغير؛ لا نستخدمه لتشخيص شخص أو مجتمع بأكمله.'},
 {'title':'ما الذي يمكن أن نبنيه؟','type':'two','left_title':'حلقة تعلم','left':['3–5 أشخاص اختياريين','قاعدة مصدر واحدة','دور متناوب وحق مرور'], 'right_title':'عادة تواصل','right':['توقف قبل المشاركة','تلخيص منصف','سؤال عن المصدر','إنصات بلا فضح']},
 {'title':'مادة الأسبوع | عدسة لا تشخيص','subtitle':'100 سؤال 65–68 + تأسيس وعي 6 و9 | M5-S16 إلى M5-S23','bullets':['العناوين تتكلم عن الهوية والروابط والتحديات بصياغات واسعة.','نحلل الآلية المقترحة والدليل والحد، لا نشخص جيلاً أو مجتمعاً.','التطبيق: تجربة تعليم/تواصل قانونية صغيرة، لا برنامج سياسي أو تعبوي.'], 'size':17},
 {'title':'نشاط E7 | حلقة تعلم لا غرفة صدى','type':'steps','steps':['هدف صغير','قاعدة مصدر','حق مرور','دور متناوب','مراجعة أسبوعية'],'note':'اسألوا: من قد يستبعده الوقت أو اللغة أو الكلفة؟ صمموا بديلاً فردياً.'},
 {'title':'نشاط E8 | تجربة 7 أيام','bullets':['اختر فعلاً واحداً: تحقق قبل مشاركة، إنصات، أو تلخيص رأي مخالف.','حدد وقتاً ومكاناً وعائقاً وخطة تخفيف.','لا تراقب الآخرين ولا تنشر عنهم ولا تسعى إلى إقناع قسري.','النجاح: ممارسة واعية ومحدودة، لا تغيير مجتمع كامل.'], 'size':18},
 {'title':'من الأثر إلى المراجعة','type':'two','left_title':'لاحظ','left':['هل خف التعميم؟','هل تحسن سؤال المصدر؟','هل تمكنت من المرور؟'], 'right_title':'راجع','right':['ما الكلفة؟','من استُبعد؟','ما التعديل الصغير؟']},
 {'title':'القياس الختامي وبوابة المراجعة','bullets':['مهمة بعدية 0–8: مصطلح/مصدر/نطاق/حد.','استبيان: الفهم والأمان والعبء والاستعمال بعد 7–10 أيام.','أي استهداف أو اختبار هوية إشارة حمراء توقف النشاط.','ما العادة التي سأحملها إلى قراءتي ومشاركتي القادمة؟'], 'size':18},
]

# DOCX
make_docx('01_facilitator_guide_module_05.md', '01_facilitator_guide_module_05.docx', 'دليل الميسر', 'الوحدة 5: الحداثة والاستعمار والهوية')
make_docx('02_learner_workbook_module_05.md', '02_learner_workbook_module_05.docx', 'دفتر المتعلم', 'الوحدة 5: الحداثة والاستعمار والهوية')
make_docx('03_activity_cards_module_05.md', '03_activity_cards_module_05.docx', 'بطاقات الأنشطة', 'الوحدة 5: الحداثة والاستعمار والهوية')
make_docx('06_release_gate_and_revision_note.md', '06_release_gate_and_revision_note.docx', 'بوابة الإصدار والمراجعة', 'الوحدة 5: الحداثة والاستعمار والهوية')
make_docx('07_pilot_protocol_module_05.md', '07_pilot_protocol_module_05.docx', 'بروتوكول تجربة Pilot', 'الوحدة 5: الحداثة والاستعمار والهوية')

# XLSX
csv_to_xlsx('04_resource_registry_v0_1.csv', '04_resource_registry_v0_1.xlsx', 'سجل الموارد')
csv_to_xlsx('05_glossary_v0_1.csv', '05_glossary_v0_1.xlsx', 'المعجم')
csv_to_xlsx('08_pilot_data_template.csv', '08_pilot_data_template.xlsx', 'Pilot data')

# PPTX
slide_deck(17, '01_week_17_occupation_colonialism_hegemony.pptx', week17)
slide_deck(18, '02_week_18_modern_state_institutions.pptx', week18)
slide_deck(19, '03_week_19_borders_palestine_secularism.pptx', week19)
slide_deck(20, '04_week_20_identity_social_cohesion.pptx', week20)

# Validate OOXML and package publishable assets plus reproducible source files.
all_files = list(OUT.glob('*.docx')) + list(OUT.glob('*.xlsx')) + list(SLIDES.glob('*.pptx'))
for path in all_files:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert '[Content_Types].xml' in names, f'Invalid OOXML: {path}'
        if path.suffix == '.docx': assert 'word/document.xml' in names
        if path.suffix == '.xlsx': assert 'xl/workbook.xml' in names
        if path.suffix == '.pptx': assert 'ppt/presentation.xml' in names

zip_path = ROOT / 'module_05_production_pack_v0_1.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file(): z.write(path, arcname=f'module_05_production_pack_v0_1/{path.relative_to(OUT)}')
    for name in ['README.md','01_facilitator_guide_module_05.md','02_learner_workbook_module_05.md','03_activity_cards_module_05.md','04_resource_registry_v0_1.csv','05_glossary_v0_1.csv','06_release_gate_and_revision_note.md','07_pilot_protocol_module_05.md','08_pilot_data_template.csv','09_validation_report_v0_1.md','create_module_05_ooxml.py']:
        z.write(ROOT / name, arcname=f'module_05_production_pack_v0_1/source/{name}')
with zipfile.ZipFile(zip_path) as z: assert z.testzip() is None
print('Created and validated:')
for path in all_files: print(path.relative_to(ROOT), path.stat().st_size)
print(zip_path.relative_to(ROOT), zip_path.stat().st_size)
