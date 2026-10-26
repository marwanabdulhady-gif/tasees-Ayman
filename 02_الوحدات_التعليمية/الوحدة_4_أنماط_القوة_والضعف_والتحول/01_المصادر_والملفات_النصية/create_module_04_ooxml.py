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

ROOT = Path('/home/user/module_04_patterns_power_weakness_transformation')
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
    set_rtl(hp); rr = hp.add_run('من اليقين إلى الوعي والعمل — الوحدة 4'); set_run_font(rr, 8.5, TEAL)
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
    add_textbox(slide, Inches(.55), Inches(7.12), Inches(12.25), Inches(.22), f'الوحدة 4 — أنماط القوة والضعف والتحول | الأسبوع {week} | مسودة إنتاجية v0.1', 7.5, MUTED)

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


# ---------------- Deck content: Module 4 ----------------
week13 = [
 {'title':'الأسبوع 13 | النجاح: شخص، مؤسسة، وسياق','subtitle':'لا عبادة للبطل ولا إنكار للفاعلية الفردية','type':'quote','quote':'«الدور الفردي قد يكون مهماً، لكنه يعمل داخل مؤسسات وشروط وسياقات لا تختصرها الحكاية البطولية.»','prompt':'ندرس القرار والقدرة والنتيجة الإنسانية؛ لا نمجّد العنف ولا نطلب موقف هوية.'},
 {'title':'مهارة اليوم وأثرها','type':'two','left_title':'مهارة تفسير','left':['فصل الشخص عن المؤسسة','رؤية السياق والتحالفات والقيود','تسمية الدليل والحد'], 'right_title':'أثر مسؤول','right':['لا نجاح = فضيلة تلقائياً','لا بطل = سبب وحيد','لا رواية ملهمة بلا سؤال']},
 {'title':'ثلاث طبقات لا تتنافس','type':'steps','steps':['شخص','مؤسسة','سياق'],'note':'قد تتفاعل الطبقات؛ لا يلغي وجود واحدة أهمية الأخرى.'},
 {'title':'أسئلة قبل حكاية البطل','type':'two','left_title':'عن الشخص','left':['ما القرار/المهارة؟','ما الدليل على أثره؟'], 'right_title':'عن الشروط','right':['ما الموارد والتنظيم؟','ما الحلفاء والخصوم والظرف؟']},
 {'title':'مادة الأسبوع | عنوان ليس تفسيراً','subtitle':'100 سؤال 35–37 | السجل M4-S01 إلى M4-S03','bullets':['الحلقة 35 تعرض عنواناً اختزالياً عن «خيانة واحدة»؛ نحلله ولا نقرره.','الحلقة 36 مناسبة لسؤال صورة القائد مقابل البنية.','الحلقة 37 حساسة عند اتهامات وعنف؛ لا تستخدم تفاصيلها بلا مراجعة موضعية.','التفريغ آلي: راجع الفيديو/المصدر الأصلي قبل أي اقتباس.'], 'size':17},
 {'title':'نشاط D1 | شخص/مؤسسة/سياق','type':'steps','steps':['ادعاء','دور شخص','قدرة مؤسسة','شرط سياق','حد'],'note':'اكتبوا نوع الدليل المطلوب تحت كل خانة، لا أسماء أو أحكام شخصية فقط.'},
 {'title':'اختبار البطل','bullets':['حوّل «فلان صنع التاريخ» إلى صياغة شروط وآليات.','أضفوا عاملاً مؤسسياً وعاملاً سياقياً قد يغيران النتيجة.','اسألوا: ما الذي لا نراه إذا ركزنا على شخصية واحدة؟','فرّقوا بين وصف القدرة وبين تبرير استخدامها.'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['عامل فردي مهم: ____________.','شرط مؤسسي أو سياقي لازم: ____________.','حد يمنع الحكاية البطولية من أن تصبح تفسيراً كاملاً: ____________.','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week14 = [
 {'title':'الأسبوع 14 | الفقد والسقوط: عيادة الأسباب','subtitle':'لا سبب واحد مريح، ولا لوم جماعي، ولا قدر تاريخي','type':'quote','quote':'«العامل القريب لا يكفي دائماً، والشرط البنيوي لا يجعل النتيجة حتمية.»','prompt':'نعترف بألم الفقد من دون أن نملأ فراغ الدليل بلغة اللوم أو الحتمية.'},
 {'title':'ستة أسئلة للسبب','type':'steps','steps':['عامل','آلية','شرط','مسرّع','بديل','حد'],'note':'ما لا نعرفه جزء من التفسير المسؤول.'},
 {'title':'عيادة لا محكمة','type':'two','left_title':'نبحث عن','left':['خارجي وداخلي','مؤسسة وموارد','أفكار وشبكات','طارئ ونتائج غير مقصودة'], 'right_title':'ولا نفترض','right':['عيباً ثابتاً في شعب','خيانة تفسر كل شيء','حتمية من نتيجة لاحقة']},
 {'title':'كلمات تحتاج دليلاً','type':'two','left_title':'«خيانة»','left':['من الفاعل؟ ما الفعل؟','ما الالتزام/المعيار؟','ما المصدر والزمن؟'], 'right_title':'«ضعف/انحدار»','right':['أي مجال أو مؤشر؟','لمن وبأي فترة؟','ما البديل التفسيري؟']},
 {'title':'مادة الأسبوع | فحص الفقد','subtitle':'100 سؤال 38–40 | السجل M4-S04 إلى M4-S06','bullets':['نستخدم مادة واحدة بعد مراجعة، لا سرداً كاملاً عن الأندلس أو الهند.','السؤال: ما العامل القريب؟ ما الشرط؟ ما الآلية؟ ما العامل الغائب؟','لا ننقل من خسارة إقليم/سلطة إلى حكم جوهري على أناس أو حضارة.'], 'size':18},
 {'title':'نشاط D3 | عيادة أسباب','type':'steps','steps':['فرّز عامل','سمِّ آلية','ابحث عن شرط','اختبر بديلاً','اكتب حد'],'note':'يمكن للبطاقة أن تقع في أكثر من خانة؛ هذا ليس نقصاً بل دقة.'},
 {'title':'سلسلة تُقطع','bullets':['اكتب: عامل → آلية → أثر.','أضف شرطاً يجعل السلسلة ممكنة، ومانعاً قد يقطعها.','استبدل «حتماً» بـ«قد» و«إذا» و«لكن».','لا تجعل عاملًا خارجياً يلغي الفاعلية الداخلية، ولا العكس.'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['تفسير محدود للفقد: __________________.','عامل غائب أو قراءة بديلة: __________________.','لفظ يحتاج تعريفاً قبل أن أستعمله: __________________.','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week15 = [
 {'title':'الأسبوع 15 | العثمانيون: المصطلح والمصدر قبل الثنائية','subtitle':'تاريخ واسع ومتعدد التجارب لا يختزل في مجد كامل أو احتلال كامل','type':'quote','quote':'«قبل الحكم الكبير: من يتكلم؟ عن أي زمن ومكان وفئة؟ وبأي معنى للكلمة؟»','prompt':'لا يُطلب من أحد الدفاع عن هوية قومية أو سياسية، ولا تُسقط المادة على الحاضر.'},
 {'title':'من الوصف إلى الحكم','type':'steps','steps':['لفظ','تعريف','نطاق','مصدر','معيار','حد'],'note':'الكلمة السياسية أو الأخلاقية ليست برهاناً؛ هي بداية سؤال.'},
 {'title':'كلمات متعددة الوظائف','type':'two','left_title':'قد تكون وصفية','left':['إمبراطورية','مركز/طرف','إصلاح','ولاية'], 'right_title':'وقد تكون معيارية','right':['احتلال','مجد','تحرر','انحدار']},
 {'title':'النطاق يغير السؤال','type':'two','left_title':'اسأل عن','left':['القرن والفترة','المنطقة والمدينة','الفئة والموقع','نوع العلاقة'], 'right_title':'ولا تعمم من','right':['مركز إلى أطراف','قرار إلى تجربة الجميع','واقعة إلى ستة قرون']},
 {'title':'مادة الأسبوع | مختبر لا حكم نهائي','subtitle':'100 سؤال 41–49 | السجل M4-S07 إلى M4-S15','bullets':['حدّدوا دعوى واحدة فقط ومادة مراجَعة قبل اللقاء.','الحلقتان 44 و47 شديدة الحساسية؛ لا تعرضان من دون تعريفات ومصادر متعددة.','نقرأ العرض بوصفه دعوى وحجة، لا قصة الدولة كاملة ولا موقفاً حاضراً.','مراجع M4-R04 إلى M4-R06 توسعية ومنهجية، لا جواب واحد بديل.'], 'size':16},
 {'title':'نشاط D5 | مختبر المصطلحات','type':'steps','steps':['اختر لفظاً','عرّفه','ضع نطاقه','سمِّ معيارك','ابحث عن مصدر'],'note':'لا تبدأ مناظرة قبل اكتمال بطاقة المصطلح.'},
 {'title':'نشاط D6 | مناظرة مصادر','bullets':['ليست مناظرة هويات؛ فرق تبني دعويين محدودتين.','كل دعوى: نطاق، مصدر، ما يثبته، تفسير، حد.','حارس الكرامة يوقف التعميم أو طلب الهوية أو الشعار الكبير.','المخرج: صياغة إنصاف لقراءة بديلة، لا فوز فريق.'], 'size':18},
 {'title':'بطاقة الخروج','bullets':['كلمة أوقفتها لأنها أكبر من تعريفها: ____________.','نطاق أحتاجه قبل الحكم: ____________.','مصدر أو قراءة أحتاجها: ____________.','وضوح/أمان/عبء: 1–5.'], 'size':19},
]
week16 = [
 {'title':'الأسبوع 16 | أفكار وشبكات ومؤسسات: التحول الطويل','subtitle':'النموذج خريطة قابلة للنقد، لا وصفة للسياسة أو تشخيص للناس','type':'quote','quote':'«الفكرة لا تغيّر وحدها: من يحملها؟ أين تستقر؟ ما الحافز والمؤسسة والضغط والوقت؟»','prompt':'نطبق على تعلم وتواصل أو مؤسسة محلية، لا على تعبئة أو صراع حاضر.'},
 {'title':'عقد التحول الممكنة','type':'steps','steps':['ضغط','قابلية','وسيط','شبكة','مؤسسة','أثر'],'note':'أضفوا التأخر الزمني والتغذية الراجعة حيث يوجد دليل أو سؤال معقول.'},
 {'title':'ما الذي لا يساويه النموذج؟','type':'two','left_title':'يساعد على','left':['تسمية الوسيط والآلية','رؤية العوامل المتفاعلة','طرح سؤال عن الدليل'], 'right_title':'ولا يثبت','right':['سبباً واحداً','حتمية مستقبلية','تشخيص مجتمع كامل']},
 {'title':'مادة الأسبوع | عدسة صاحبها','subtitle':'تأسيس وعي: 1–2 والمستوى الثاني 1–2 | M4-S16 إلى M4-S19','bullets':['تقدم المواد إطاراً عن الأفكار والشبكات والمؤسسات.','نسأل: ما الذي يضيئه الإطار؟ ما الذي قد يغفله؟ ما الدليل اللازم لحالة محددة؟','أي موضع عن 1492 أو تحول كبير يراجعه الميسر قبل العرض.','لا يحول الإطار إلى برنامج سياسي أو حكم على واقع المشاركين.'], 'size':17},
 {'title':'نشاط D7 | خريطة التحول','type':'steps','steps':['سؤال محدد','عقد وأسهم','دليل/افتراض','شرط/مانع','حد'],'note':'ضعوا دالاً بجوار الدليل وفاءً بجوار الافتراض، واسألوا عن السهم الغائب.'},
 {'title':'اختبار القطع والتأخير','bullets':['أين يمكن أن تنقطع السلسلة؟ وما الذي قد يعكس اتجاهها؟','هل يوجد تأخر زمني بين العامل والأثر؟','هل يعود الأثر فيقوي/يضعف العملية؟ لا تدّعوا ذلك بلا آلية.','اكتبوا ما الذي لا تدعيه الخريطة بوضوح.'], 'size':18},
 {'title':'من نموذج إلى تطبيق آمن','type':'two','left_title':'اختبر خريطتك','left':['ما السهم بلا دليل؟','ما العامل الغائب؟','أين يمكن القطع أو التأخير؟'], 'right_title':'حدّد التطبيق','right':['تعلم أو تواصل أو مؤسسة صغيرة','لا وصفة سياسية أو تعبئة','خطوة مدنية قابلة للمراجعة']},
 {'title':'القياس الختامي وبوابة المراجعة','bullets':['مهمة بعدية 0–8: شخص/مؤسسة/سياق، عامل/آلية/حد.','استبيان: الوضوح، الأمان، العبء، واستعمال المهارة بعد 7–10 أيام.','أي لوم جماعي أو تمجيد للعنف إشارة حمراء توقف الحالة فوراً.','ما الاختصار التفسيري الذي سأقاومه في قراءتي القادمة؟'], 'size':18},
]

# DOCX
make_docx('01_facilitator_guide_module_04.md', '01_facilitator_guide_module_04.docx', 'دليل الميسر', 'الوحدة 4: أنماط القوة والضعف والتحول')
make_docx('02_learner_workbook_module_04.md', '02_learner_workbook_module_04.docx', 'دفتر المتعلم', 'الوحدة 4: أنماط القوة والضعف والتحول')
make_docx('03_activity_cards_module_04.md', '03_activity_cards_module_04.docx', 'بطاقات الأنشطة', 'الوحدة 4: أنماط القوة والضعف والتحول')
make_docx('06_release_gate_and_revision_note.md', '06_release_gate_and_revision_note.docx', 'بوابة الإصدار والمراجعة', 'الوحدة 4: أنماط القوة والضعف والتحول')
make_docx('07_pilot_protocol_module_04.md', '07_pilot_protocol_module_04.docx', 'بروتوكول تجربة Pilot', 'الوحدة 4: أنماط القوة والضعف والتحول')

# XLSX
csv_to_xlsx('04_resource_registry_v0_1.csv', '04_resource_registry_v0_1.xlsx', 'سجل الموارد')
csv_to_xlsx('05_glossary_v0_1.csv', '05_glossary_v0_1.xlsx', 'المعجم')
csv_to_xlsx('08_pilot_data_template.csv', '08_pilot_data_template.xlsx', 'Pilot data')

# PPTX
slide_deck(13, '01_week_13_success_person_institution_context.pptx', week13)
slide_deck(14, '02_week_14_loss_collapse_cause_clinic.pptx', week14)
slide_deck(15, '03_week_15_ottomans_terms_sources_before_binary.pptx', week15)
slide_deck(16, '04_week_16_ideas_networks_institutions_transformation.pptx', week16)

# Validate OOXML and package publishable assets plus reproducible source files.
all_files = list(OUT.glob('*.docx')) + list(OUT.glob('*.xlsx')) + list(SLIDES.glob('*.pptx'))
for path in all_files:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert '[Content_Types].xml' in names, f'Invalid OOXML: {path}'
        if path.suffix == '.docx': assert 'word/document.xml' in names
        if path.suffix == '.xlsx': assert 'xl/workbook.xml' in names
        if path.suffix == '.pptx': assert 'ppt/presentation.xml' in names

zip_path = ROOT / 'module_04_production_pack_v0_1.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file(): z.write(path, arcname=f'module_04_production_pack_v0_1/{path.relative_to(OUT)}')
    for name in ['README.md','01_facilitator_guide_module_04.md','02_learner_workbook_module_04.md','03_activity_cards_module_04.md','04_resource_registry_v0_1.csv','05_glossary_v0_1.csv','06_release_gate_and_revision_note.md','07_pilot_protocol_module_04.md','08_pilot_data_template.csv','09_validation_report_v0_1.md','create_module_04_ooxml.py']:
        z.write(ROOT / name, arcname=f'module_04_production_pack_v0_1/source/{name}')
with zipfile.ZipFile(zip_path) as z: assert z.testzip() is None
print('Created and validated:')
for path in all_files: print(path.relative_to(ROOT), path.stat().st_size)
print(zip_path.relative_to(ROOT), zip_path.stat().st_size)
