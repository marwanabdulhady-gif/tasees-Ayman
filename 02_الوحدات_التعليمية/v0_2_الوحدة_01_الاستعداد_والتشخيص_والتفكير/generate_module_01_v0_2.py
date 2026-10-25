#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 01 v0.2 OOXML outputs and an auditable ZIP."""
from pathlib import Path
import csv, zipfile, hashlib, shutil
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from pptx import Presentation
from pptx.util import Inches as PInches, Pt as PPt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor as PRGB

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'01_source_text_assets'; OUT=ROOT/'02_working_outputs'; FINAL=ROOT/'03_final_package'
OUT.mkdir(exist_ok=True); FINAL.mkdir(exist_ok=True)

from docx.enum.text import WD_BREAK
AR_FONT='Arial'; NAVY='16324F'; TEAL='167D8D'; GOLD='D69E2E'; PALE='EAF4F5'; INK='17212B'; MUTED='52616B'; WHITE='FFFFFF'; LIGHT='F7FAFC'; RED='A61B29'

def bidi(p):
    pPr=p._p.get_or_add_pPr(); e=OxmlElement('w:bidi');e.set(qn('w:val'),'1');pPr.append(e)
def runstyle(r,size=10.5,bold=False,color=INK):
    r.font.name=AR_FONT; r._element.rPr.rFonts.set(qn('w:cs'),AR_FONT);r.font.size=Pt(size);r.bold=bold;r.font.color.rgb=RGBColor.from_string(color)
def para(doc,text='',style=None,size=10.5,bold=False,color=INK,after=5,align=WD_ALIGN_PARAGRAPH.RIGHT):
    p=doc.add_paragraph(style=style);p.alignment=align;bidi(p);p.paragraph_format.space_after=Pt(after);p.paragraph_format.line_spacing=1.12
    runstyle(p.add_run(text),size,bold,color);return p
def shade(cell,color):
    tcPr=cell._tc.get_or_add_tcPr();shd=OxmlElement('w:shd');shd.set(qn('w:fill'),color);tcPr.append(shd)
def cell_text(cell,text,bold=False,color=INK,size=8.5):
    cell.text='';p=cell.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);p.paragraph_format.space_after=Pt(0);r=p.add_run(str(text));runstyle(r,size,bold,color);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
def table(doc,heads,rows,widths=None,size=8.5):
    t=doc.add_table(rows=1,cols=len(heads));t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for c,h in zip(t.rows[0].cells,heads): shade(c,NAVY);cell_text(c,h,True,WHITE,size)
    trPr=t.rows[0]._tr.get_or_add_trPr();h=OxmlElement('w:tblHeader');h.set(qn('w:val'),'true');trPr.append(h)
    for ri,row in enumerate(rows):
        cells=t.add_row().cells
        for c,val in zip(cells,row):
            if ri%2==0: shade(c,LIGHT)
            cell_text(c,val,False,INK,size)
    if widths:
        for row in t.rows:
            for c,w in zip(row.cells,widths):c.width=Inches(w)
    return t
def bullets(doc,items):
    for x in items:
        p=doc.add_paragraph(style='List Bullet');p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);p.paragraph_format.space_after=Pt(2);runstyle(p.add_run(x),10)
def init_doc(title,subtitle):
    d=Document();s=d.styles;s['Normal'].font.name=AR_FONT;s['Normal']._element.rPr.rFonts.set(qn('w:cs'),AR_FONT);s['Normal'].font.size=Pt(10.5)
    for st,sz,co in [('Title',25,NAVY),('Heading 1',17,NAVY),('Heading 2',13,TEAL),('Heading 3',11,GOLD)]:
        s[st].font.name=AR_FONT;s[st]._element.rPr.rFonts.set(qn('w:cs'),AR_FONT);s[st].font.size=Pt(sz);s[st].font.color.rgb=RGBColor.from_string(co)
    sec=d.sections[0];sec.top_margin=Inches(.55);sec.bottom_margin=Inches(.55);sec.left_margin=Inches(.58);sec.right_margin=Inches(.58)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);runstyle(p.add_run(title),25,True,NAVY);p.paragraph_format.space_after=Pt(4)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);runstyle(p.add_run(subtitle),12,False,TEAL);p.paragraph_format.space_after=Pt(12)
    hp=sec.header.paragraphs[0];hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(hp);runstyle(hp.add_run('تأسيس وعي المسلم المعاصر | الوحدة 1 v0.2'),8,True,TEAL)
    fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER;runstyle(fp.add_run('إصدار إنتاجي v0.2  •  25 أكتوبر 2026'),8,False,MUTED)
    return d

weeks={
1:{'title':'الاستعداد: من التشتت إلى خريطة تعلم','q':'كيف أتعلم وفق خريطة بدلاً من تجميع معلومات لا تتحول إلى فهم أو ممارسة؟','out':'سؤال محدد + خريطة تعلم + عادة 14 يوماً','src':'AT-00 (PDF 9–53)؛ تأسيس وعي 1؛ 100 سؤال 1','act':'A1 خريطة التعلم + A2 من المصدر إلى عادة','agenda':[('0–12','دخول آمن: كثرة المعلومات تعني وعياً؟'),('12–25','اتفاق الحوار وحق المرور'),('25–40','نموذج سؤال/فجوة/مصدر/خطوة'),('40–62','A1 خريطة التعلم'),('62–72','استراحة وكتابة صامتة'),('72–94','مختبر مواد أولية'),('94–110','A2 عادة 14 يوماً'),('110–120','بطاقة خروج')]},
2:{'title':'التشخيص بلا وصم: وصف ومعيار ودليل','q':'كيف أصف مشكلة أو سلوكاً أو مؤسسة بدقة بلا تحويل المفهوم المعياري إلى تسمية للناس؟','out':'بطاقة تشخيص: وصف + معيار + شاهد + بديل + حد','src':'AT-01 (PDF 54–99)؛ 100 سؤال 2؛ ACRL/Wineburg','act':'A3 تشريح التسمية + A4 عيادة التشخيص','agenda':[('0–12','فرز: ملاحظة/تفسير/حكم/دعوة'),('12–28','شرح طبقات الكلام وأثر التسمية'),('28–58','A3 تشريح التسمية'),('58–70','معرض صامت'),('70–80','استراحة/كتابة مجهلة'),('80–101','A4 عيادة التشخيص'),('101–113','تطبيق تاريخي محدود'),('113–120','إعادة كتابة دقيقة')]},
3:{'title':'تحرير العقل: دعوى ودليل وافتراض وبديل','q':'ما التفكير المنضبط بين الانفعال السريع والارتياب الدائم؟','out':'بطاقة D-S-I-A-B-L مع درجة ثقة مبررة','src':'AT-04 (PDF 214–271)؛ رحلة اليقين 20؛ ACRL/Wineburg','act':'A5 محكمة دعوى + A6 سؤال قابل للبحث','agenda':[('0–12','عنوانان لنفس حدث افتراضي'),('12–28','نموذج D-S-I-A-B-L'),('28–57','A5 محكمة دعوى'),('57–67','استراحة'),('67–88','مختبر طبقات السؤال'),('88–108','A6 سؤال قابل للبحث'),('108–120','افتراض وبديل وخروج')]},
4:{'title':'التلقي المسؤول والحوار المنصف','q':'كيف أتعلم من مصدر ومن شخص مختلف، وأتحاور بإنصاف، ثم أستمر في عادة تعلم متواضعة؟','out':'وظيفة مصدر + steelman + خطة 14/30 يوماً','src':'AT-10 (PDF 547–583)؛ 100 سؤال 3؛ Brookfield/Preskill','act':'A7 تدرج المصدر + A8 steelman وخطة تعلم','agenda':[('0–15','مهمة بعدية قصيرة'),('15–30','وظيفة المصدر وحده'),('30–56','A7 تدرج المصدر'),('56–67','استراحة'),('67–93','A8 steelman وحوار'),('93–108','خطة 14/30'),('108–120','إغلاق الوحدة')]}}

# 1 facilitator
d=init_doc('دليل الميسر','الوحدة 1 v0.2 | الاستعداد والتشخيص والتفكير')
para(d,'وظيفة الوحدة','Heading 1',17,True);para(d,'تعلّم هذه الوحدة المتعلم أن يحول السؤال إلى دعوى محددة ومصدر وحد وخطوة تعلم. المواد الجديدة من «أين الطريق؟» مادة أولية ذات منظور معياري؛ لا تعامل كإجماع ولا تستخدم لوصف الناس أو قياس المعتقد.')
para(d,'اتفاق الحوار','Heading 2',13,True);bullets(d,['نفحص الدعوى لا الشخص أو الهوية أو النية.','نسمي الوصف والتفسير والحكم والدعوة قبل النقد.','لا تطبيق لمفهوم معياري على شخص أو جماعة أو دولة حاضرة.','حق المرور والحالة الافتراضية والبديل الكتابي محفوظ.','الفعل التعليمي صغير وقانوني ولا يتضمن مراقبة أو تعبئة.'])
for n,w in weeks.items():
    para(d,f'الأسبوع {n} — {w["title"]}','Heading 1',17,True)
    para(d,'السؤال المحرك: '+w['q'],None,11,True,TEAL)
    table(d,['الوقت','التنفيذ'],w['agenda'],[1.0,5.9],8.5)
    para(d,'المواد والمخرج','Heading 2',13,True);table(d,['مواد متتبعة','النشاط','المخرج'],[(w['src'],w['act'],w['out'])],[2.7,2.0,2.2],8.2)
    para(d,'أسئلة ميسرة','Heading 2',13,True)
    qs={1:['هل سؤالي سؤال معرفة أم معنى أم قرار؟','ما الذي لا تثبته المادة وحدها؟','ما أصغر خطوة تعلم قابلة للاستمرار؟'],2:['ما الفرق بين وصف فعل وتسمية مجموعة؟','ما التفسير المنافس؟','من قد يتضرر من تسمية عامة؟'],3:['ما الافتراض الذي يربط الشاهد بالدعوى؟','ما نوع الدليل الملائم لهذا السؤال؟','كيف أذكر الحد بلا مساواة المعرفة بالتخمين؟'],4:['ماذا يقدم هذا المصدر وفي أي مجال؟','هل سيقبل صاحب القراءة الأخرى ملخصي؟','ما عادة التعلم التي أستطيع مراجعتها بعد 14 يوماً؟']}[n]
    bullets(d,qs)
    para(d,'تكييف المستويات','Heading 2',13,True)
    bullets(d,['مستكشف: قالب جاهز وحالة افتراضية.','ممارس: صلة بقرار/حوار يومي من دون كشف شخصي.','متقدم: مصدران من نوعين، افتراض وقراءة بديلة وحد موثق.'])
para(d,'سجل بعد اللقاء','Heading 1',17,True);table(d,['سؤال مراجعة','ملاحظة/قرار'],[('أين خُلط الوصف بالتفسير أو الحكم؟',''),('هل ظهر وسم جماعي أو اختبار اعتقاد؟',''),('ما موضع المصدر الذي يحتاج مراجعة الأصل؟',''),('هل كان حق المرور والعبء مناسبين؟','')],[3.8,3.1],9)
d.save(OUT/'01_facilitator_guide_module_01_v0_2.docx')

# 2 workbook
d=init_doc('دفتر المتعلم','الوحدة 1 v0.2 | أوراق السؤال والتشخيص والتفكير')
para(d,'قاعدة الدفتر','Heading 1',17,True);para(d,'سؤال محدد، مصدر معلوم، حد صريح، وخطوة صغيرة قابلة للمراجعة.',None,11,True,TEAL)
forms={1:[('خريطة التعلم',['السؤال','لماذا يهمني؟','ما أعرفه','ما أفترضه','ما أجهله','مصدر أول','خطوة 10 دقائق']),('عادة 14 يوماً',['الإشارة','الفعل','وقت واقعي','مقياس العبء','موعد المراجعة'])],2:[('بطاقة اللغة الدقيقة',['العبارة الأصلية','نوعها','إعادة كتابة دقيقة']),('عيادة تشخيص',['سلوك/قرار محدد','شاهد/مصدر','معيار معلن','تفسير بديل','حد','أثر تسمية','وصف بلا وصم'])],3:[('D-S-I-A-B-L',['الدعوى','الشاهد/المصدر','الاستدلال','الافتراض','البديل','الحد','درجة الثقة 0–4']),('طبقات السؤال',['الجملة','الطبقة','الدليل أو الحوار الملائم'])],4:[('وظيفة المصدر',['المصدر','ما يقدمه','ما لا يكفي فيه','خطوة مكملة']),('steelman وخطة 14/30',['القراءة الأخرى','أقوى صياغة عادلة','سؤال مصدر','حد','عادة تعلم','مراجعة 14/30'])]}
for n,w in weeks.items():
    para(d,f'الأسبوع {n} | {w["title"]}','Heading 1',17,True);para(d,w['q'],None,11,True,TEAL)
    for title,fields in forms[n]:
        para(d,title,'Heading 2',13,True);table(d,['الحقل','إجابتي/ملاحظتي'],[(x,'\n\n') for x in fields],[2.6,4.3],9)
    para(d,'مراجعة ذاتية: وضوح ___/5  |  أمان في السؤال/المرور ___/5  |  عبء ___/5  |  استعمال مهارة ___/5',None,10,False,TEAL)
d.save(OUT/'02_learner_workbook_module_01_v0_2.docx')

# 3 activity cards
d=init_doc('بطاقات الأنشطة','A1–A8 | الوحدة 1 v0.2')
cards=[('A1','خريطة التعلم','22','سؤال، معرفة متاحة، فجوة، مصدر، خطوة. لا تشارك سؤالاً حساساً إلا برغبتك.'),('A2','من المصدر إلى عادة','18','صنف الفكرة: وصف/تفسير/حكم/دعوة؛ اذكر حدها؛ صمم عادة 10 دقائق.'),('A3','تشريح التسمية','25','استخرج ملاحظة وتفسيراً وحكماً وأثر تسمية من حالة افتراضية. لا ملصقات هوية.'),('A4','عيادة التشخيص','20','معيار، شاهد، بديل، حد. حارس الكرامة يوقف الحكم على مجموعات.'),('A5','محكمة دعوى D-S-I-A-B-L','30','صاحب دعوى وباحث مصدر وباحث بديل وحارس حد ومقرر. النجاح هو الافتراض والحد.'),('A6','سؤال قابل للبحث','18','حول عبارة حادة إلى سؤال محدد ودليل لازم وخطوة تحقق وما لا يثبته.'),('A7','تدرج المصدر ووظيفته','20','حدد ما الذي يفيده به كل مصدر وحده؛ لا ترتب قيمة الأشخاص أو الجماعات.'),('A8','steelman وخطة تعلم','25','ملخص عادل وسؤال مصدر وحد وخطة 14/30؛ لا نقد قبل قبول الملخص.')]
for code,title,time,inst in cards:
    para(d,f'{code} | {title}','Heading 1',16,True,NAVY);para(d,f'الوقت: {time} دقيقة',None,10,True,GOLD);para(d,inst,None,11)
    table(d,['قبل البدء','المخرج','حاجز الأمان'],[('حق المرور وحالة افتراضية','ورقة/خريطة قابلة للتتبع','دعوى لا شخص؛ لا اختبار اعتقاد؛ لا وسم')],[2.1,2.3,2.6],8.5)
d.save(OUT/'03_activity_cards_module_01_v0_2.docx')

# 4 registry glossary
d=init_doc('سجل الموارد والمعجم','الوحدة 1 v0.2 | التتبع وحدود الاستعمال')
para(d,'قاعدة الاستعمال','Heading 1',17,True);para(d,'ورود المصدر في corpus لا يعني توصية أو تحققاً نهائياً. تفريغات PDF/captions أدلة موضعية للبحث؛ يُراجع الأصل قبل الاقتباس أو بناء دعوى تعليمية.')
resources=[]
with open(SRC/'04_resource_registry_module_01_v0_2.csv',encoding='utf-8') as f:
    for r in csv.DictReader(f): resources.append((r['resource_id'],r['short_title'],r['role_in_module'],r['week'],r['verification_status']))
table(d,['المعرّف','المادة','الدور','الأسبوع','الحالة'],resources,[.85,1.8,1.9,.6,1.7],7.3)
para(d,'مصطلحات محورية','Heading 1',17,True)
terms=[]
with open(SRC/'05_glossary_module_01_v0_2.csv',encoding='utf-8') as f:
    for r in csv.DictReader(f): terms.append((r['term_ar'],r['plain_definition'],r['example_or_prompt']))
table(d,['المصطلح','تعريف مبسط','سؤال/مثال'],terms,[1.2,3.4,2.1],7.8)
d.save(OUT/'04_resource_registry_and_glossary_module_01_v0_2.docx')

# 5 assessment pilot
d=init_doc('التقويم وبروتوكول Pilot','الوحدة 1 v0.2 | فهم وأمان وعبء وأثر')
para(d,'المهمة الختامية','Heading 1',17,True);para(d,'خريطة تعلم أو بطاقة تشخيص بلا وصم أو عيادة دعوى أو دليل حوار. يظهر فيها سؤال ومصدر وحد وقراءة بديلة وفعل منخفض المخاطر. لا يقاس موقف ديني أو سياسي أو هوية.')
rub=[('السؤال والنطاق','غائم','واسع','محدد','محدد وحدوده معلنة'),('مصدر وشاهد','غائب','مصدر عام','مصدر مناسب','مصدر ووظيفة وحد'),('طبقات الكلام','خلط','طبقة واحدة','فصل معقول','فصل مع افتراض/جسر'),('إنصاف وكرامة','وصم/سخرية','لغة قابلة للتحسين','ملخص عادل','حد وأثر تسمية'),('فعل ومراجعة','وعد كبير','خطوة غامضة','عادة واقعية','توقف/تعديل ومراجعة')]
table(d,['المعيار','0','1','2','3'],rub,[1.3,1.2,1.2,1.2,1.9],8)
para(d,'Pilot','Heading 1',17,True);para(d,'10–20 بالغاً. موافقة ورمز منفصل وحق مرور. قبل/بعد: مهمتان من 8، مع قياس أسبوعي للوضوح والأمان والعبء واستعمال المهارة. أي وسم جماعي أو اختبار اعتقاد يعامل كإشارة حمراء لا كبيان قابل للنقاش.')
table(d,['اللون','العتبة','الإجراء'],[('أخضر','70%+ طبقة/مصدر/حد؛ 80%+ أمان 4–5','استمر مع تحسين صغير'),('أصفر','50–69% أو عبء/خلط متكرر','قلل التحضير وزد نموذجاً محلولاً'),('أحمر','وسم/اختبار اعتقاد أو أمان أقل من 60%','أوقف النشاط وأعد التصميم')],[1.0,2.7,3.7],9)
d.save(OUT/'05_assessment_and_pilot_module_01_v0_2.docx')

# Excel functions
def init_ws(ws,title,headers,rows,widths):
    ws.title=title;ws.sheet_view.rightToLeft=True;ws.freeze_panes='A2';ws.append(headers)
    for row in rows:ws.append(list(row))
    for c in ws[1]:c.fill=PatternFill('solid',fgColor=NAVY);c.font=Font(name=AR_FONT,bold=True,color=WHITE);c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font=Font(name=AR_FONT,size=10,color=INK);c.alignment=Alignment(horizontal='right',vertical='top',wrap_text=True);c.border=Border(bottom=Side(style='hair',color='D9E2E8'))
            if c.row%2==0:c.fill=PatternFill('solid',fgColor=LIGHT)
    for i,w in enumerate(widths,1):ws.column_dimensions[chr(64+i)].width=w
    ws.row_dimensions[1].height=30;ws.auto_filter.ref=ws.dimensions
# 6 operations
wb=Workbook();ws=wb.active
rows=[]
for n,w in weeks.items():
    for ti,act in w['agenda']:rows.append((n,ti,act,w['src'],w['out'],'مستكشف: قالب | ممارس: تطبيق | متقدم: مصدر وبديل'))
init_ws(ws,'خريطة التشغيل',['الأسبوع','الوقت','الفقرة','المواد','المخرج','تكييف المسارات'],rows,[10,13,39,30,28,38])
ws2=wb.create_sheet();init_ws(ws2,'سجل المخاطر',['المجال','الخطر','الحاجز','الإجراء'],[('لغة','وسم جماعي','حالة افتراضية وفصل الوصف/الحكم','أوقف وأعد الصياغة'),('مصدر','اقتباس آلي غير دقيق','مراجعة PDF/فيديو الأصل','تجميد الاقتباس'),('هوية','اختبار اعتقاد','مرور وبديل كتابي','تصعيد للميسر'),('تطبيق','فعل واسع أو ضار','عادة تعليمية صغيرة قابلة للإيقاف','تصغير/إيقاف')],[18,35,35,25])
wb.save(OUT/'06_operations_map_module_01_v0_2.xlsx')
# 7 registry workbook
wb=Workbook();ws=wb.active
with open(SRC/'04_resource_registry_module_01_v0_2.csv',encoding='utf-8') as f: rr=list(csv.DictReader(f))
init_ws(ws,'سجل الموارد',['المعرّف','العنوان','الدور','الأسبوع','الموضع','الحالة','الحاجز'],[(r['resource_id'],r['short_title'],r['role_in_module'],r['week'],r['precise_locator'],r['verification_status'],r['verification_notes']) for r in rr],[15,28,28,11,34,25,40])
ws2=wb.create_sheet()
with open(SRC/'05_glossary_module_01_v0_2.csv',encoding='utf-8') as f: tt=list(csv.DictReader(f))
init_ws(ws2,'المعجم',['المصطلح','المقابل','التعريف','التمييز','سؤال'],[(r['term_ar'],r['term_en_proposed'],r['plain_definition'],r['distinguish_from'],r['example_or_prompt']) for r in tt],[20,24,50,28,38])
wb.save(OUT/'07_resource_registry_and_glossary_module_01_v0_2.xlsx')
# 8 pilot
wb=Workbook();ws=wb.active
headers=['رمز','المسار','الوقت','المقياس','القيمة','ملاحظة اختيارية','إجراء','خصوصية']
rows=[('P001','young_adult','pre','الموافقة','نعم','','','مفتاح منفصل'),('P001','young_adult','pre','مهمة A (0–4)','','','','تجميعي'),('P001','young_adult','pre','مهمة B (0–4)','','','','تجميعي')]
for n in range(1,5):
    for m in ['الوضوح 1–5','الأمان في السؤال/المرور 1–5','ملاءمة العبء 1–5','استعمال المهارة 1–5']:rows.append(('P001','young_adult',f'week{n}',m,'','','','تجميعي'))
rows += [('GROUP','all','week2','وسم جماعي/اختبار اعتقاد (عدد)','','','مراجعة فورية','بلا أسماء'),('P001','young_adult','post','مهمة A (0–4)','','','','تجميعي'),('P001','young_adult','post','مهمة B (0–4)','','','','تجميعي'),('P001','young_adult','day30','استمرار عادة نعم/جزئي/لا','','','','اختياري')]
init_ws(ws,'متتبع Pilot',headers,rows,[14,18,14,35,13,35,22,16])
ws2=wb.create_sheet();init_ws(ws2,'لوحة قرار',['المؤشر','الهدف','القيمة','القرار'],[('تمييز طبقة/مصدر/حد','70%+','',''),('أمان 4–5','80%+','',''),('وسم/اختبار اعتقاد','0','',''),('أمان أقل من 60%','0','','أوقف/أعد التصميم')],[30,18,14,30])
wb.save(OUT/'08_pilot_tracker_module_01_v0_2.xlsx')

# PPT helpers
def set_text(shape,text,size=18,bold=False,color=INK,align=PP_ALIGN.RIGHT):
    tf=shape.text_frame;tf.clear();tf.word_wrap=True;tf.margin_left=PInches(.12);tf.margin_right=PInches(.12);tf.margin_top=PInches(.06);tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    p=tf.paragraphs[0];p.alignment=align;pr=p._p.get_or_add_pPr();bi=OxmlElement('a:bidi');bi.set('val','1');pr.append(bi)
    r=p.add_run();r.text=text;r.font.name=AR_FONT;r.font.size=PPt(size);r.font.bold=bold;r.font.color.rgb=PRGB.from_string(color)
def box(slide,x,y,w,h,text,fill=WHITE,line='D5E3E7',size=18,bold=False,color=INK,round=True):
    sh=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if round else MSO_SHAPE.RECTANGLE,PInches(x),PInches(y),PInches(w),PInches(h));sh.fill.solid();sh.fill.fore_color.rgb=PRGB.from_string(fill);sh.line.color.rgb=PRGB.from_string(line);set_text(sh,text,size,bold,color);return sh
def title(slide,n,text,sub=''):
    sh=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,PInches(13.333),PInches(.6));sh.fill.solid();sh.fill.fore_color.rgb=PRGB.from_string(NAVY);sh.line.fill.background();box(slide,.45,.1,12.4,.32,f'الوحدة 1 v0.2  |  الأسبوع {n}',NAVY,NAVY,11,True,WHITE,False);box(slide,.55,.8,12.1,.55,text,WHITE,WHITE,25,True,NAVY,False)
    if sub:box(slide,.62,1.38,11.8,.35,sub,WHITE,WHITE,13,False,TEAL,False)
def footer(slide,n):box(slide,.45,7.1,12.4,.18,f'تأسيس وعي المسلم المعاصر  •  إصدار v0.2  •  {n}/8',WHITE,WHITE,8,False,MUTED,False)
def deck(n):
    w=weeks[n];p=Presentation();p.slide_width=PInches(13.333);p.slide_height=PInches(7.5);blank=p.slide_layouts[6];sl=[]
    s=p.slides.add_slide(blank);title(s,n,w['title'],w['q']);box(s,.85,2.0,11.6,1.15,w['out'],PALE,PALE,23,True,NAVY);box(s,1.2,3.7,10.9,.8,'المعيار: دقة السؤال والمصدر والحد والكرامة، لا تبني موقف شخصي.',LIGHT,LIGHT,17,False,INK);sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'خريطة اللقاء','تحضير موجّه + ورشة حية + تجربة تعلم صغيرة');a1='\n'.join([f'{a} | {b}' for a,b in w['agenda'][:4]]);a2='\n'.join([f'{a} | {b}' for a,b in w['agenda'][4:]]);box(s,.65,1.95,5.9,3.8,a1,WHITE,'C8DDE1',15);box(s,6.8,1.95,5.9,3.8,a2,WHITE,'C8DDE1',15);box(s,1.0,6.05,11.3,.55,'حق المرور والحالة الافتراضية والكتابة البديلة متاحة دائماً.',PALE,PALE,15,True,TEAL);sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'أداة التفكير لهذا الأسبوع');keys={1:['سؤال','معرفة متاحة','فجوة','مصدر','خطوة ومراجعة'],2:['وصف','تفسير','حكم/معيار','أثر تسمية','حد'],3:['دعوى','شاهد','استدلال','افتراض/بديل','حد'],4:['وظيفة مصدر','قراءة عادلة','سؤال','حد','خطة تعلم']}[n]
    for i,x in enumerate(keys):box(s,.72+i*2.5,2.4,2.12,1.35,x,PALE if i%2==0 else LIGHT,PALE if i%2==0 else 'DDE5EB',17,True,NAVY if i%2==0 else INK)
    box(s,1.05,4.7,11.1,.75,'اسأل: ما الذي يمكن أن أقوله بدقة؟ وما الذي لا يسمح لي الدليل بقوله؟',WHITE,GOLD,20,True,GOLD);sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'المصدر وحده لا يكفي');box(s,.75,1.9,5.9,3.3,'المادة المصدرية\n'+w['src']+'\n\nتُستخدم لتحديد دعوى أو سؤال أو لغة تحتاج تحليلاً.',LIGHT,'DDE5EB',18,True,NAVY);box(s,6.75,1.9,5.9,3.3,'حاجز الاستعمال\nراجع الأصل قبل الاقتباس.\nسمِّ نوع الدعوى.\nأضف المصدر الملائم للعلم/التاريخ/الفقه.',PALE,PALE,18,True,TEAL);box(s,1.1,5.7,11.1,.5,'لا وسم للناس، ولا اختبار اعتقاد، ولا تحويل المصدر إلى سلطة شاملة.',WHITE,RED,15,True,RED);sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'الورشة الحية: '+w['act']);steps={1:['1. ارسم السؤال والفجوة.','2. سمِّ المصدر وحدّه.','3. صمم عادة 10 دقائق.'],2:['1. افصل الوصف عن الحكم.','2. أضف شاهداً وبديلًا.','3. اكتب بلا تسمية جماعية.'],3:['1. اكتب الدعوى والشاهد.','2. سمِّ الافتراض والبديل.','3. قل الحد ودرجة الثقة.'],4:['1. اشرح وظيفة المصدر.','2. قوِّ القراءة الأخرى.','3. اختر عادة 14/30.']}[n]
    for i,x in enumerate(steps):
        box(s,1.0,2.05+i*1.3,11.2,.88,x,PALE if i==1 else WHITE,TEAL if i==1 else 'DDE5EB',19,i==1,NAVY)
    sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'المسارات الثلاثة');tr=[('مستكشف 18–30','قالب واضح ومثال قريب ومهارة واحدة.'),('ممارس عام','صلة بحياة التعلم والعمل والأسرة بلا إفصاح شخصي.'),('باحث/معلّم','مصدران، افتراض، بديل، وحد موثق.')]
    for i,(a,b) in enumerate(tr):box(s,.72+i*4.18,2.0,3.75,3.25,a+'\n\n'+b,PALE if i==1 else LIGHT,TEAL if i==1 else 'DDE5EB',18,True,NAVY if i==1 else INK)
    box(s,1.0,5.85,11.2,.5,'عمق مختلف، وكرامة متساوية، ولا ترتيب للأشخاص أو المعتقدات.',WHITE,GOLD,15,True,GOLD);sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'ما الذي سنلاحظه؟');e={1:'سؤال + فجوة + مصدر + خطوة 14 يوماً.',2:'وصف + معيار + شاهد + بديل + حد.',3:'D-S-I-A-B-L + ثقة مبررة.',4:'وظيفة مصدر + steelman + خطة 14/30.'}[n]
    box(s,.75,1.9,11.8,1.0,e,PALE,PALE,21,True,NAVY);box(s,.75,3.3,3.65,2.1,'وضوح\nنوع الكلام؟',LIGHT,'DDE5EB',20,True,INK);box(s,4.82,3.3,3.65,2.1,'أمان\nهل أستطيع السؤال أو المرور؟',PALE,PALE,20,True,TEAL);box(s,8.9,3.3,3.65,2.1,'عبء\nهل الخطة واقعية؟',LIGHT,'DDE5EB',20,True,INK);sl.append(s)
    s=p.slides.add_slide(blank);title(s,n,'قبل أن نغادر');pr={1:['سؤال سأصغره','فجوة سأعترف بها','عادة سأجربها'],2:['تعميم سأعيد كتابته','حد سأضيفه','كرامة سأحميها'],3:['افتراض سأفحصه','بديل سأسمعه','حد سأصرح به'],4:['مصدر سأحدد وظيفته','قراءة سأقويها','موعد مراجعة سأحترمه']}[n]
    for i,x in enumerate(pr):box(s,.85,1.8+i*1.25,11.6,.8,x+'  ______________________________________________',WHITE,'C8DDE1',18,False,NAVY)
    box(s,1.35,5.9,10.65,.62,'التعلم المسؤول: سؤال واضح، مصدر معلوم، حد صريح، وكرامة محفوظة.',NAVY,NAVY,18,True,WHITE);sl.append(s)
    assert len(sl)==8
    for i,x in enumerate(sl,1):footer(x,i)
    p.save(OUT/f'{9+n:02d}_week_{n}_meeting_slides_module_01_v0_2.pptx')
for n in weeks:deck(n)

# final README, validation, ZIP
readme='''# الحزمة النهائية — الوحدة 1 v0.2

## الاستعداد والتشخيص والتفكير

هذه إعادة بناء مستقلة للوحدة الأولى بعد دمج corpus `أين الطريق؟` مع corpora البرنامج السابقة. لا تستبدل حزمة الوحدة 1 v0.1.

## المحتوى
- أربعة أسابيع: خريطة تعلم، تشخيص بلا وصم، دعوى/دليل/بديل/حد، وتلقي مسؤول.
- ثلاثة مسارات للمتعلمين.
- حواجز: لا اختبار اعتقاد، لا وسم جماعي، لا انتقاء/تجنيد، ولا فعل تعبوي/رقابي.
- كل مصدر يحمل وظيفة وحداً وحالة تحقق.

## التوزيع
- `01_source_text_assets/`: 9 أصول نصية وقوالب.
- `02_working_outputs/`: 5 DOCX و3 XLSX و4 PPTX.
- `03_final_package/`: هذا README وتقرير التحقق.
'''
(FINAL/'README_module_01_v0_2.md').write_text(readme,encoding='utf-8')
checks=[]
def chk(a,b,c):checks.append((a,b,c))
for f in sorted(OUT.glob('*.docx')):
    try:
        x=Document(f);chk(f.name,bool('\n'.join(p.text for p in x.paragraphs).strip()),f'{len(x.paragraphs)} paragraphs; {len(x.tables)} tables')
    except Exception as e:chk(f.name,False,str(e))
for f in sorted(OUT.glob('*.xlsx')):
    try:x=load_workbook(f,read_only=True);chk(f.name,len(x.sheetnames)>=1,f'{len(x.sheetnames)} worksheets')
    except Exception as e:chk(f.name,False,str(e))
for f in sorted(OUT.glob('*.pptx')):
    try:x=Presentation(f);chk(f.name,len(x.slides)==8,f'{len(x.slides)} slides (required 8)')
    except Exception as e:chk(f.name,False,str(e))
source_files=sorted(SRC.glob('*'))
chk('source_asset_count',len(source_files)==9,f'{len(source_files)} source assets (required 9)')
chk('production_output_count',len(list(OUT.iterdir()))==12,f'{len(list(OUT.iterdir()))} production outputs (required 12)')
report=['# تقرير تحقق — الوحدة 1 v0.2','','تاريخ التشغيل: 2026-10-25','','| العنصر | النتيجة | التفاصيل |','|---|---|---|']
for a,b,c in checks:report.append(f'| `{a}` | {"PASS" if b else "FAIL"} | {c} |')
report+=['','## مراجعة تحريرية','- العروض الأربعة تحوي 8 شرائح لكل أسبوع.','- أضيفت مواد أين الطريق بوصفها مادة أولية متتبعة ومحدودة الاستعمال، لا مرجعاً مستقلاً أو إجماعاً.','- تضم الوحدة حواجز ضد الوصم الجماعي واختبار الاعتقاد والانتقاء/التجنيد والفعل التعبوي.','']
(FINAL/'validation_report_module_01_v0_2.md').write_text('\n'.join(report),encoding='utf-8')
zip_path=ROOT/'module_01_v0_2_production_pack.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(FINAL/'README_module_01_v0_2.md','03_final_package/README_module_01_v0_2.md')
    z.write(FINAL/'validation_report_module_01_v0_2.md','03_final_package/validation_report_module_01_v0_2.md')
    for f in source_files:z.write(f,'01_source_text_assets/'+f.name)
    for f in sorted(OUT.iterdir()):z.write(f,'02_working_outputs/'+f.name)
with zipfile.ZipFile(zip_path) as z:
    chk('final_zip_integrity',z.testzip() is None,f'{len(z.namelist())} entries (required 23)')
    chk('final_zip_entry_count',len(z.namelist())==23,f'{len(z.namelist())} entries')
report=['# تقرير تحقق — الوحدة 1 v0.2','','تاريخ التشغيل: 2026-10-25','','| العنصر | النتيجة | التفاصيل |','|---|---|---|']
for a,b,c in checks:report.append(f'| `{a}` | {"PASS" if b else "FAIL"} | {c} |')
report+=['','## مراجعة تحريرية','- العروض الأربعة تحوي 8 شرائح لكل أسبوع.','- أضيفت مواد أين الطريق بوصفها مادة أولية متتبعة ومحدودة الاستعمال، لا مرجعاً مستقلاً أو إجماعاً.','- تضم الوحدة حواجز ضد الوصم الجماعي واختبار الاعتقاد والانتقاء/التجنيد والفعل التعبوي.','']
(FINAL/'validation_report_module_01_v0_2.md').write_text('\n'.join(report),encoding='utf-8')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(FINAL/'README_module_01_v0_2.md','03_final_package/README_module_01_v0_2.md');z.write(FINAL/'validation_report_module_01_v0_2.md','03_final_package/validation_report_module_01_v0_2.md')
    for f in source_files:z.write(f,'01_source_text_assets/'+f.name)
    for f in sorted(OUT.iterdir()):z.write(f,'02_working_outputs/'+f.name)
print('ZIP',zip_path.name,'entries',len(zipfile.ZipFile(zip_path).namelist()),'MD5',hashlib.md5(zip_path.read_bytes()).hexdigest())
for a,b,c in checks:print('PASS' if b else 'FAIL',a,c)
if not all(x[1] for x in checks):raise SystemExit(1)
