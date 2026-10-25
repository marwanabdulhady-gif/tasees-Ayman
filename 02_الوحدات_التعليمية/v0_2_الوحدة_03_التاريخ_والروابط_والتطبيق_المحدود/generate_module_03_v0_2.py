#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Module 03 v0.2: historical reading, relationships, and bounded application."""
from __future__ import annotations
import csv, hashlib, json, shutil, zipfile
from pathlib import Path
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from pptx import Presentation
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches as PInches, Pt as PPt

ROOT=Path('/home/user'); OLD=ROOT/'module_03_power_conflict_belonging'; M2REG=ROOT/'module_02_message_meaning_practice_v0_2/01_source_text_assets/04_resource_registry_module_02_v0_2.csv'; BLUE=ROOT/'course_revision_v0_2_ayn_al_tariq'
OUTROOT=ROOT/'module_03_history_relationships_boundaries_v0_2'; DESIGN=OUTROOT/'00_design_and_trace'; SRC=OUTROOT/'01_source_text_assets'; WORK=OUTROOT/'02_working_outputs'; FINAL=OUTROOT/'03_final_package'; ZIP=OUTROOT/'module_03_v0_2_production_pack.zip'
AR_FONT='Arial'; NAVY='16324F'; TEAL='167D8D'; GOLD='D69E2E'; PALE='EAF4F5'; INK='17212B'; MUTED='52616B'; WHITE='FFFFFF'; LIGHT='F7FAFC'; RED='A61B29'
WEEKS={
9:{'title':'الاستعداد والقدرة والفرصة: قراءة بلا نخبوية','question':'كيف نفهم الاستعداد والقدرة والفرصة في سياق تاريخي من غير نخبوية أو انتقاء للناس أو تجنيد؟','at':'AT-03: المؤهلات (PDF 181–213)','other':'100 سؤال 18–21 مادة تاريخية حساسة تختار منها حالة قصيرة بعد مراجعة الأصل','output':'خريطة شخص/فرصة/مؤسسة/سياق/حد، مع تمييز القدرة من القيمة الأخلاقية.','activities':'C1 خريطة فرصة وسياق + C2 سلم الادعاء','guard':'لا تقييم «صلاح» أو أهلية أو استعداد للمشاركين، ولا انتقاء أو تجنيد أو هرمية مكانة.','agenda':[('0–12','اتفاق تاريخ حساس وحق المرور'),('12–28','شرح: قدرة/فرصة/مؤسسة/سياق ≠ قيمة شخص'),('28–55','C1 خريطة فرصة وسياق'),('55–67','معرض صامت: ما الدليل وما الحد؟'),('67–77','استراحة وأسئلة مكتوبة'),('77–97','حالة تاريخية قصيرة بعد مراجعة الأصل'),('97–111','C2 سلم الادعاء'),('111–120','خروج: ما الذي لا تسمح الخريطة بالحكم به؟')]},
10:{'title':'الفتنة والسلطة والخلاف: مصدر لا هوية','question':'كيف نقرأ الفتنة والسلطة والخلاف بخرائط مصادر لا بهويات متصارعة أو محكمة عقدية؟','at':'AT-09: إعادة صياغة الروابط والعلاقات (PDF 476–546) بوصفها عدسة للعلاقات لا برنامجاً تنظيمياً','other':'100 سؤال 18–26: corpus تاريخي؛ يراجع الميسر الفيديو ويستخدم موضعاً واحداً محدوداً','output':'خط زمني: حدث/مصدر/قراءة/لايقين/أثر لغة، مع صياغة لا تسمي جماعات حاضرة.','activities':'C3 خط زمني متعدد المصادر + C4 محاكمة الادعاء لا الشخص','guard':'لا محكمة عقدية أو طائفية، ولا تصنيف لأشخاص أو جماعات حاضرة، ولا استنباط سياسة أو عنف.','agenda':[('0–12','فرز واقعة/رواية/تفسير/حكم/استعمال حاضر'),('12–27','شرح مصدر/زمن/تلقٍ/حد'),('27–54','C3 خط زمني متعدد المصادر'),('54–66','جولة أسئلة مصدر صامتة'),('66–76','استراحة وحالة بديلة'),('76–96','C4 محاكمة الادعاء لا الشخص'),('96–110','تحليل لغة: ما أثر التسمية؟'),('110–120','خروج: مصدر مطلوب وحد معلن')]},
11:{'title':'الروابط وجماعة التعلم: دور وقاعدة ومراجعة','question':'كيف تصنع الروابط جماعة تعلم من غير إذابة الفروق أو ولاء تنظيمي أو سلطة على الضمير؟','at':'AT-09: إعادة صياغة الروابط والعلاقات (PDF 476–546)','other':'100 سؤال 27–31: أمثلة تاريخية للنظم والعلاقات؛ لا تُستعمل كوصفة تنظيمية','output':'قيمة/دور/قاعدة فريق/اعتراض/مراجعة، وخريطة نظم تسمي الافتراض والحد.','activities':'C5 خريطة النظم + C6 ميثاق العلاقة والمراجعة','guard':'جماعة التعلم مؤقتة ومدنية/تعليمية؛ لا تجنيد أو ولاء أو مراقبة أو سلطة دينية.','agenda':[('0–12','ما الفرق بين الصحبة والدعم والسيطرة؟'),('12–28','شرح: دور ≠ قيمة شخص، قاعدة ≠ ولاء'),('28–57','C5 خريطة النظم'),('57–67','اختبار صوت غائب وعامل مفقود'),('67–77','استراحة'),('77–98','C6 ميثاق العلاقة والمراجعة'),('98–111','اختبار اعتراض آمن ودور متناوب'),('111–120','خروج: قاعدة تحمي الكرامة')]},
12:{'title':'مبدأ وواقعة وتفسير وتطبيق محدود','question':'ما الفرق بين الرسالة والتاريخ والتطبيق المعاصر، وكيف نحول مبدأً إلى درس محدود لا مشروع حكم أو إقصاء؟','at':'AT-13: فهم حقائق الإسلام الكبرى (PDF 716–767)','other':'100 سؤال 5–8 و32–34: مراكز متعددة وحركة معرفة؛ لا تعميم حضاري ولا قراءة طائفية','output':'خريطة مبدأ/واقعة/تفسير/تطبيق محدود + معرض تاريخي صغير متعدد المراكز.','activities':'C7 معرض اتصال متعدد المراكز + C8 مبدأ إلى تطبيق محدود','guard':'لا استنباط مشروع حكم أو تنظيم أو إقصاء، ولا تحويل التاريخ إلى شعار أو وصفة سياسية.','agenda':[('0–12','جسر: المبدأ ليس واقعة والواقعة ليست سياسة'),('12–27','شرح الطبقات الأربع وحدود التطبيق'),('27–55','C7 معرض اتصال متعدد المراكز'),('55–67','جولة متحف: سؤال مصدر وحد'),('67–77','استراحة'),('77–97','C8 مبدأ إلى تطبيق محدود'),('97–110','مذكرة حالة: دليل وقراءة بديلة'),('110–120','قياس بعدي وإغلاق الوحدة')]},
}
QUESTIONS={
9:['ما الفرق بين القدرة أو الفرصة وبين قيمة الإنسان؟','ما الذي لا تثبته خريطة الفاعل والمؤسسة والسياق؟','كيف تمنع لغة المؤهلات من تحويل التعلم إلى انتقاء؟'],
10:['ما الفرق بين واقعة مزعومة ورواية وتفسير وحكم؟','كيف تغير معرفة زمن المصدر أو غرضه سؤالنا؟','كيف نحترم الذاكرة الدينية من غير أن نجعلها بديلاً عن كل أدوات التاريخ؟'],
11:['ما الفرق بين علاقة دعم ودور منظم وولاء؟','ما الذي يجعل قاعدة الفريق عادلة لمن يملك وقتاً أو سلطة أقل؟','كيف تسمي سهماً في خريطة النظم: دليل أم افتراض؟'],
12:['ما الفرق بين مبدأ وواقعة وتفسير وتطبيق؟','ما الذي ينبغي أن يتغير قبل أن ننقل درساً تاريخياً إلى الحاضر؟','ما الذي لا يحق لنا استنباطه من المصدر؟'],
}
LEVELS={
9:['مستكشف: خمس خانات وحالة افتراضية.','ممارس: يصف فرصة/حاجزاً في مؤسسة تعلم بلا أسماء.','متقدم: مصدران وبديل وحد وتحيز اختيار.'],
10:['مستكشف: أربع بطاقات وعمود لا أعرف.','ممارس: يعيد صياغة حكم متداول إلى سؤال مصدر/نطاق.','متقدم: يقارن مصدرين ويصرح بمعيار وحد.'],
11:['مستكشف: ست عقد وثلاثة أسهم.','ممارس: ميثاق فريق تعلم محدود المدة.','متقدم: يميز بين علاقة سببية وتزامن ووساطة.'],
12:['مستكشف: بطاقة معرض واحدة.','ممارس: درس مدني/تعليمي صغير قابل للإيقاف.','متقدم: مذكرة مصدر/بديل وتطبيق محدود مع اختلاف السياق.'],
}

def clean():
 if OUTROOT.exists(): shutil.rmtree(OUTROOT)
 for p in (DESIGN,SRC,WORK,FINAL): p.mkdir(parents=True,exist_ok=True)
def wt(path,text): path.write_text(text.strip()+'\n',encoding='utf8')

def sources():
 wt(OUTROOT/'README.md','''# الوحدة 3 v0.2 — التاريخ والروابط والتطبيق المحدود

**الأسابيع:** 9–12 من برنامج 24 أسبوعاً.  
**السؤال الجامع:** كيف تُبنى روابط وجماعة ورسالة تاريخياً وأخلاقياً من غير طائفية أو تجنيد أو استنباط مشروع سياسي؟  
**الحالة:** بناء مستقل v0.2؛ يحفظ v0.1 كما هي.

## التحول
تضيف هذه النسخة خيوط `أين الطريق؟` حول المؤهلات والروابط وحقائق الإسلام الكبرى، لكنها تحوّلها إلى أسئلة قابلة للتتبع والنقد. لا يصبح مفهوم المؤهلات أداة اختيار للناس، ولا تصبح الروابط ولاءً تنظيمياً، ولا تتحول «الحقائق الكبرى» إلى استنباط مشروع حكم.

## حواجز
لا محكمة عقدية أو طائفية؛ لا وسم لجماعات حاضرة؛ لا تجنيد أو ولاء؛ لا سلطة دينية؛ لا تبرير للعنف أو الإقصاء؛ ولا نقل مباشر من التاريخ إلى سياسة معاصرة.
''')
 shutil.copy2(BLUE/'01_master_rebuild_blueprint_v0_2.md',DESIGN/'01_master_rebuild_blueprint_v0_2.md')
 wt(DESIGN/'00_revision_scope_module_03_v0_2.md','''# نطاق الوحدة 3 v0.2

- تحفظ الوحدة 3 v0.1 في مجلدها الأصلي.
- تضيف AT-03 وAT-09 وAT-13 كمواد أولية ذات منظور معياري.
- تستقبل مواد السيرة الحساسة التي سجّلتها الوحدة 2 v0.2 بوصفها مواد انتقالية محتملة؛ لا تتحول إلى مناظرة هوية.
- تضيف حواجز ضد النخبوية، والطائفية، والولاء التنظيمي، والقياس من التاريخ إلى الحاضر.
''')
 trace=[
 ['M3V2-AT03',9,'أين الطريق','03-الخطوة_الثانية_اكتساب_مؤهلات_الخروج_من_الظلمات_إلى_النور.md','PDF 181–213','قدرة/فرصة/سياق','معياري/تربوي','تصدير corpus','راجع PDF','لا انتقاء أو تقييم صلاح'],
 ['M3V2-AT09','10–11','أين الطريق','09-الخطوة_الثامنة_إعادة_صياغة_الروابط_والعلاقات.md','PDF 476–546','علاقات وروابط','معياري/تربوي','تصدير corpus','ميز العدسة عن الوقائع','لا ولاء أو تنظيم أو سلطة'],
 ['M3V2-AT13',12,'أين الطريق','13-الخطوة_الثانية_عشرة_فهم_حقائق_الإسلام_الكبرى.md','PDF 716–767','مبدأ/واقعة/تطبيق','ديني/معياري','تصدير corpus','حدد الطبقة','لا مشروع حكم أو إقصاء'],
 ['M3V2-S18',10,'100 سؤال في التاريخ','18-من-قتل-عثمان-ومن-بدأ-ببذور-الفتنة-100.md','فيديو/تفريغ محلي','قراءة تاريخية حساسة','تاريخي/تفسيري','هوية مثبتة','راجع الفيديو','لا حكم طائفي'],
 ['M3V2-S22',10,'100 سؤال في التاريخ','22-بنو-أمية-100-سؤال-في-التاريخ.md','فيديو/تفريغ محلي','سياق سلطة','تاريخي/تفسيري','هوية مثبتة','نطاق ومصدر','لا نقل سياسي مباشر'],
 ['M3V2-S27',11,'100 سؤال في التاريخ','27-الثورة-العباسية-100-سؤال-في-التاريخ.md','فيديو/تفريغ محلي','خريطة نظم','تاريخي/تفسيري','هوية مثبتة','مصدر وحد','لا وصفة تنظيمية'],
 ['M3V2-S07',12,'100 سؤال في التاريخ','07-كيف-تعامل-المسلمون-مع-إرث-حضارات-الأمم-الأخرى-100.md','فيديو/تفريغ محلي','انتقال معرفة','تاريخي/تفسيري','هوية مثبتة','وسيط وحد','لا تعميم حضاري'],
 ['M3V2-M01','9–12','Wineburg','Historical Thinking and Other Unnatural Acts','2001','تصميم مهارة','تربوي','تحقق سابق','للميسر','ليس مرجع تاريخ إسلامي'],
 ]
 with open(DESIGN/'01_source_trace_matrix_module_03_v0_2.csv','w',encoding='utf8',newline='') as f:
  w=csv.writer(f);w.writerow(['source_id','week','corpus','source_file_or_title','precise_locator','role','claim_type','verification_status','required_action','content_guardrail']);w.writerows(trace)
 wt(DESIGN/'02_revision_and_source_trace_module_03_v0_2.md','''# خريطة التعديل والتتبع — الوحدة 3 v0.2

| v0.1 | v0.2 |
|---|---|
| الفتنة والسلطة كمادة تاريخ حساسة | مصدر/زمن/قراءة/لايقين/أثر لغة؛ لا هوية أو محكمة عقدية |
| الحاكم والخلاف | شخص/فرصة/مؤسسة/سياق/حد؛ لا نخبوية أو شخصنة |
| النظم والعلاقات | دور/قاعدة/اعتراض/مراجعة؛ لا ولاء تنظيمي |
| المراكز والتبادل | مبدأ/واقعة/تفسير/تطبيق محدود؛ لا مشروع حكم |

- [ ] الأصل مرئي للميسر قبل الاقتباس.
- [ ] لا تسمية لجماعة حاضرة ولا سؤال عن الهوية.
- [ ] كل سهم/استنتاج يحمل دليلاً أو افتراضاً أو حدّاً.
- [ ] كل تطبيق مدني/تعليمي صغير وقابل للإيقاف.
''')
 # source guides
 fac=['# دليل الميسر — الوحدة 3 v0.2','','## وظيفة الوحدة','ليست الغاية توحيد رأي عن التاريخ المبكر، بل بناء قدرة على فصل الواقعة والرواية والتفسير والحكم والاستعمال المعاصر. تظل مواد `أين الطريق؟` صوتاً معيارياً متتبعاً، لا أداة انتقاء أو ولاء أو استنباط سياسة.','','## اتفاق الحوار','1. نفحص رواية أو مصدر أو دعوى، لا جوهر جماعة بشرية.','2. لا يعلن أحد هوية أو نسباً أو موقفاً عقدياً أو سياسياً.','3. يحق المرور والحالة الافتراضية والكتابة الصامتة.','4. السياق يفسر ولا يبرر تلقائياً؛ والحكم لا يلغي سؤال الدليل.','5. لا تأخذ جماعة التعلم دور حزب أو سلطة أو جهة علاج.','']
 for n,w in WEEKS.items():
  fac += [f'# الأسبوع {n} — {w["title"]}','','## السؤال',w['question'],'','## المادة ووظيفتها',f'- **أين الطريق:** {w["at"]}.',f'- **مرافقة:** {w["other"]}.','- راجع الأصل قبل أي اقتباس، ولا تعرض أكثر من حالة قصيرة حساسة في اللقاء.','','## خطة 120 دقيقة','| الزمن | التنفيذ |','|---:|---|']+[f'| {a} | {b} |' for a,b in w['agenda']]+['','## أسئلة ميسرة']+[f'- {x}' for x in QUESTIONS[n]]+['','## تكييف المستويات']+[f'- {x}' for x in LEVELS[n]]+['','## حاجز',w['guard'],'','## دليل تحقق','المخرج: '+w['output'],'']
 wt(SRC/'01_facilitator_guide_module_03_v0_2.md','\n'.join(fac))
 wb=['# دفتر المتعلم — الوحدة 3 v0.2','','**قاعدة الدفتر:** لا أكتب حكماً أكبر من دليلي، ولا أحول سؤال التاريخ إلى حكم على إنسان حاضر أو مشروع للمستقبل.','']
 forms={9:[('خريطة شخص/فرصة/مؤسسة/سياق',['الادعاء أو الحالة','الفاعل/الفرصة','المؤسسة/السياق','ما الدليل؟','قراءة بديلة','ما الذي لا يعنيه هذا عن قيمة الأشخاص؟']),('سلم الادعاء',['الحالة الضيقة','ما الدليل المطلوب لتوسيعها؟','حد يمنع التعميم'])],10:[('خط زمني متعدد المصادر',['الزمن','الواقعة كما تُروى','المصدر/الراوي','قراءة أو تفسير','ما لا أعلمه']),('محاكمة الادعاء',['الدعوى','النطاق','الدليل المباشر','القراءة البديلة','أثر اللغة','الحد'])],11:[('خريطة النظم والروابط',['العلاقة أو الدور','دليل/افتراض','صوت أو عامل غائب','حد العلاقة']),('ميثاق جماعة تعلم',['قيمة','دور متناوب','قاعدة مصدر/حوار','اعتراض آمن','مراجعة'])],12:[('مبدأ/واقعة/تفسير/تطبيق محدود',['المبدأ','الواقعة/المصدر','التفسير','تطبيق مدني/تعليمي محدود','ما لا أستنبطه']),('بطاقة معرض',['ما الذي تحرك؟','مركزان/وسيط','دليل','قراءة بديلة','حد'])]}
 for n,w in WEEKS.items():
  wb += [f'# الأسبوع {n} | {w["title"]}','',w['question'],'']
  for title,fields in forms[n]:wb += [f'## {title}','| الحقل | ملاحظتي |','|---|---|']+[f'| {x} |  |' for x in fields]+['']
  wb += ['**خروج:** وضوح ___/5 | أمان السؤال/المرور ___/5 | عبء ___/5 | هل ذكرت مصدراً وحداً؟ ___/5','']
 wt(SRC/'02_learner_workbook_module_03_v0_2.md','\n'.join(wb))
 wt(SRC/'03_activity_cards_module_03_v0_2.md','''# بطاقات أنشطة — الوحدة 3 v0.2

## C1 | خريطة فرصة وسياق
**25 دقيقة.** حالة تاريخية أو افتراضية: شخص/فرصة/مؤسسة/سياق/دليل/حد. النجاح هو منع تحويل «القدرة» إلى معيار فضل أو انتقاء.

## C2 | سلم الادعاء
**15 دقيقة.** انتقل من واقعة ضيقة إلى فترة أو دولة ثم لاحظ الدليل الإضافي المطلوب. توقف قبل الحكم على جماعة حاضرة.

## C3 | خط زمني متعدد المصادر
**25 دقيقة.** بطاقات: واقعة مزعومة/مصدر/تفسير/ذاكرة لاحقة/سؤال مفتوح. لا بطاقة بلا موضع أو حد.

## C4 | محاكمة الادعاء لا الشخص
**25 دقيقة.** الأدوار: مصوغ دعوى، محقق مصدر، محدد نطاق، قراءة بديلة، حارس كرامة. المخرج: «يدعم المصدر ___ في نطاق ___؛ لا يكفي لـ___».

## C5 | خريطة النظم والروابط
**30 دقيقة.** عقد وأسهم: أدوار ومؤسسات ومعرفة واقتصاد وأطراف. ضع (د) للدليل و(ف) للافتراض، وحدد صوتاً غائباً.

## C6 | ميثاق العلاقة والمراجعة
**20 دقيقة.** قيمة، دور متناوب، قاعدة مصدر، اعتراض آمن، مراجعة. ليست جماعة ولاء ولا قناة متابعة شخصية.

## C7 | معرض اتصال متعدد المراكز
**25 دقيقة.** لوحة: شيء تحرك + مركزان + وسيط + مصدر + حد. لا تقول «انتقل» إن كان الدليل يثبت تزامناً فقط.

## C8 | مبدأ إلى تطبيق محدود
**18 دقيقة.** اكتب: مبدأ/واقعة/تفسير/تطبيق مدني أو تعليمي صغير/ما لا أستنبطه. يمنع مشروع الحكم أو الإقصاء.
''')
 # registry preserve M3 v0.1 and add AT and deferred M2 sources
 old=list(csv.DictReader(open(OLD/'04_resource_registry_v0_1.csv',encoding='utf8')))
 fields=['resource_id','short_title','creator_or_body','year_or_date','format','language','source_locator','week_or_role','verification_status','editorial_handling','claim_risk','content_guardrail']
 rows=[]
 for r in old:
  rows.append({'resource_id':'M3V2-'+r['resource_id'],'short_title':r['title'],'creator_or_body':r['creator_or_responsible_body'],'year_or_date':r['date_or_year'],'format':r['format'],'language':r['language'],'source_locator':r['source_locator'],'week_or_role':r['module_use'],'verification_status':r['verification_status'],'editorial_handling':r['editorial_handling'],'claim_risk':r['claim_risk'],'content_guardrail':'راجع الأصل وحدد المصدر/النطاق/الحد قبل الاستخدام.'})
 at=[('M3V2-AT03','أين الطريق؟ — اكتساب المؤهلات','المصدر المرفق؛ تصدير Markdown','الطبعة الأولى','PDF/transcription','ar','episodes_markdown/03…md; PDF 181–213','W9: قدرة/فرصة/سياق','تصدير corpus؛ راجع PDF','مادة أولية','مرتفع','لا انتقاء أو تقييم صلاح أو نخبوية'),('M3V2-AT09','أين الطريق؟ — إعادة صياغة الروابط','المصدر المرفق؛ تصدير Markdown','الطبعة الأولى','PDF/transcription','ar','episodes_markdown/09…md; PDF 476–546','W10–11: عدسة روابط','تصدير corpus؛ راجع PDF','مادة أولية','مرتفع','لا ولاء تنظيمي أو سلطة أو تجنيد'),('M3V2-AT13','أين الطريق؟ — فهم حقائق الإسلام الكبرى','المصدر المرفق؛ تصدير Markdown','الطبعة الأولى','PDF/transcription','ar','episodes_markdown/13…md; PDF 716–767','W12: مبدأ/واقعة/تطبيق','تصدير corpus؛ راجع PDF','مادة أولية','مرتفع','لا مشروع حكم أو إقصاء')]
 for val in at: rows.append(dict(zip(fields,val)))
 if M2REG.exists():
  m2=list(csv.DictReader(open(M2REG,encoding='utf8')))
  for r in m2:
   if r['resource_id'] in {'M2V2-M2-S05','M2V2-M2-S06','M2V2-M2-S07','M2V2-M2-S08','M2V2-M2-S09'}:
    d=dict(r);d['resource_id']='M3V2-INHERITED-'+r['resource_id'].split('-')[-1];d['week_or_role']='مسجل منتقل من الوحدة 2؛ لا يستخدم إلا بعد مراجعة محتوى في W10';rows.append({k:d.get(k,'') for k in fields})
 with open(SRC/'04_resource_registry_module_03_v0_2.csv','w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 # glossary preserve / normalize
 oldg=list(csv.DictReader(open(OLD/'05_glossary_v0_1.csv',encoding='utf8')))
 gs=[]
 for r in oldg:gs.append({'term_ar':r['term'],'term_en_proposed':'','plain_definition':r['working_definition'],'boundary':r['caution_or_boundary'],'week':r['module_use']})
 gs += [{'term_ar':'فرصة','term_en_proposed':'opportunity','plain_definition':'شروط أو منافذ تمكن فاعلاً من عمل محتمل ضمن سياق.','boundary':'ليست برهاناً على فضل الشخص أو استحقاقه.','week':'9'},{'term_ar':'مؤهلات','term_en_proposed':'capacities','plain_definition':'مهارات أو معرفة أو علاقات أو موارد قد تؤثر في القدرة على الفعل.','boundary':'لا تستخدم لترتيب المتعلمين أو تجنيدهم.','week':'9'},{'term_ar':'رابط','term_en_proposed':'relationship tie','plain_definition':'صلة بين أشخاص أو أدوار أو مؤسسات يمكن وصف أثرها وحدودها.','boundary':'لا تتحول إلى ولاء أو سلطة على الضمير.','week':'10-11'},{'term_ar':'دور متناوب','term_en_proposed':'rotating role','plain_definition':'مسؤولية محددة تتبدل لتمنع الامتياز الثابت وتدعم المراجعة.','boundary':'لا يساوي قدرة على الحكم في الهوية أو الاعتقاد.','week':'11'},{'term_ar':'تطبيق محدود','term_en_proposed':'bounded application','plain_definition':'خطوة مدنية/تعليمية صغيرة تستلهم مبدأ بعد تسمية اختلاف السياق.','boundary':'ليس مشروع حكم أو وصفة سياسية.','week':'12'}]
 with open(SRC/'05_glossary_module_03_v0_2.csv','w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(gs[0]));w.writeheader();w.writerows(gs)
 wt(SRC/'06_release_gate_and_revision_note_module_03_v0_2.md','''# بوابة الإصدار والمراجعة — الوحدة 3 v0.2
- [ ] راجع كل موضع أصل قبل العرض؛ لا transcript فقط.
- [ ] الحالات التاريخية الحساسة محددة كتابةً ومسار البديل جاهز.
- [ ] لا توجد صياغة تطلب هوية/نسباً/موقفاً أو تسمية لجماعة حاضرة.
- [ ] الأنشطة لا تنتج توصية سياسية أو ولاءً أو متابعة شخصية.
- [ ] يوجد سجل سؤال معلّق وإحالة عند الضيق.

| القرار | الشرط | الإجراء |
|---|---|---|
| ابدأ | 70%+ يميزون واقعة/مصدر/تفسير/حد و80%+ أمان | شغّل بحالات محدودة ومصدر مرئي. |
| مخفف | التباس متوسط أو عبء مرتفع | حالتان افتراضيتان وكتابة صامتة أكثر. |
| أوقف | طائفية/شخصنة/استهداف أو أمان <60% | أوقف الحالة وأعد التدريب واللغة. |
''')
 wt(SRC/'07_pilot_protocol_module_03_v0_2.md','''# بروتوكول Pilot — الوحدة 3 v0.2

## الغرض
اختبار مهارات المصدر والنطاق والحد وخريطة النظم والتطبيق المحدود، وأمان الحوار التاريخي. لا يقيس هوية أو اعتقاداً أو موقفاً طائفياً أو سياسياً.

## العينة والخصوصية
10–20 بالغاً؛ رمز منفصل عن الاسم؛ حق المرور/حالة افتراضية/كتابة بديلة؛ لا تسجيلات أو قصص شخصية. أي إشارة استهداف أو ضغط توقف الحالة فوراً.

## القياس
| الوقت | أداة | ما تقيس |
|---|---|---|
| قبل W9 | مهمة 0–8 | واقعة/مصدر/تفسير/حد + نطاق |
| كل أسبوع | وضوح/أمان/عبء/استعمال مهارة 1–5 | تصميم لا عقيدة |
| أثناء اللقاء | ملاحظة مجهلة | سؤال مصدر، حد، إنصاف، طائفية/شخصنة/تدخل |
| بعد W12 | مهمة 0–8 + معرض مصغر | خريطة مصدر وتطبيق محدود |
| 7–10 أيام | سؤال اختياري | هل تحققت من مصدر أو ذكرت حداً قبل مشاركة رواية؟ |

## عتبات
أخضر: 70%+ مصدر/نطاق/حد و80%+ أمان. أصفر: تخفيف المصدر وزيادة الكتابة. أحمر: أي وسم/استهداف/دعوة ولاء أو أمان أقل من 60%؛ أوقف النشاط وأعد التصميم.
''')
 pilot=[['consent','P001','explorer','pre','consent_confirmed','yes','','facilitator','Separate key'],['baseline','P001','explorer','pre','layers_source_scope_limit_0_4','','','researcher','No ranking'],['baseline','P001','explorer','pre','systems_or_bounded_application_0_4','','','researcher','No ranking']]
 for n in range(9,13):
  for metric in ['clarity_1_5','safety_to_ask_or_pass_1_5','workload_fit_1_5','skill_use_1_5']:pilot.append(['survey','P001','explorer',f'week{n}',metric,'','','facilitator','Aggregate only'])
  pilot += [['observation','GROUP','all',f'week{n}','source_scope_limit_named_count','','','observer','No names'],['observation','GROUP','all',f'week{n}','sectarian_or_personalizing_language_count','','','observer','Immediate review; no names']]
 pilot += [['post','P001','explorer','post','layers_source_scope_limit_0_4','','','researcher','No ranking'],['follow_up','P001','explorer','day7_10','source_check_or_limit_yes_partial_no','','','facilitator','Optional']]
 with open(SRC/'08_pilot_data_template_module_03_v0_2.csv','w',encoding='utf8',newline='') as f:w=csv.writer(f);w.writerow(['record_type','participant_code','track','week_or_timepoint','item_or_metric','value','optional_comment_or_evidence','owner','privacy_note']);w.writerows(pilot)
 wt(SRC/'09_revision_and_source_trace_module_03_v0_2.md','''# خريطة التعديل والتتبع — الوحدة 3 v0.2

| الخيط | الأسبوع | الاستخدام | الحاجز |
|---|---:|---|---|
| AT-03 المؤهلات | 9 | شخص/فرصة/مؤسسة/سياق | لا نخبوية أو انتقاء |
| AT-09 الروابط | 10–11 | عدسة علاقات وميثاق تعلم | لا ولاء أو سلطة |
| AT-13 الحقائق الكبرى | 12 | مبدأ/واقعة/تفسير/تطبيق | لا مشروع حكم أو إقصاء |

مواد السيرة الحساسة المسجلة في الوحدة 2 تبقى متتبعة، ولا تدخل إلا بحالة محددة، ومصدر مرئي، وبديل افتراضي، وميسر مدرب على بروتوكول التاريخ الحساس.
''')
# OOXML helpers
def bidi(p):
 pPr=p._p.get_or_add_pPr();e=OxmlElement('w:bidi');e.set(qn('w:val'),'1');pPr.append(e)
def run(r,size=10.5,bold=False,color=INK):r.font.name=AR_FONT;r._element.rPr.rFonts.set(qn('w:cs'),AR_FONT);r.font.size=Pt(size);r.bold=bold;r.font.color.rgb=RGBColor.from_string(color)
def para(d,text='',style=None,size=10.5,bold=False,color=INK):
 p=d.add_paragraph(style=style);p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);p.paragraph_format.space_after=Pt(5);p.paragraph_format.line_spacing=1.12;run(p.add_run(str(text)),size,bold,color);return p
def shade(c,color):tc=c._tc.get_or_add_tcPr();x=OxmlElement('w:shd');x.set(qn('w:fill'),color);tc.append(x)
def cell(c,text,bold=False,color=INK,size=8.5):
 c.text='';p=c.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);p.paragraph_format.space_after=Pt(0);run(p.add_run(str(text)),size,bold,color);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
def tbl(d,heads,rows,widths=None,size=8.5):
 t=d.add_table(rows=1,cols=len(heads));t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for c,h in zip(t.rows[0].cells,heads):shade(c,NAVY);cell(c,h,True,WHITE,size)
 for i,row in enumerate(rows):
  cs=t.add_row().cells
  for c,v in zip(cs,row):
   if i%2==0:shade(c,LIGHT)
   cell(c,v,False,INK,size)
 if widths:
  for row in t.rows:
   for c,w in zip(row.cells,widths):c.width=Inches(w)
 return t
def bullets(d,items):
 for x in items:
  p=d.add_paragraph(style='List Bullet');p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);run(p.add_run(x),10)
def doc(title,sub):
 d=Document();s=d.styles;s['Normal'].font.name=AR_FONT;s['Normal']._element.rPr.rFonts.set(qn('w:cs'),AR_FONT);s['Normal'].font.size=Pt(10.5)
 for st,sz,col in [('Title',25,NAVY),('Heading 1',17,NAVY),('Heading 2',13,TEAL)]:s[st].font.name=AR_FONT;s[st]._element.rPr.rFonts.set(qn('w:cs'),AR_FONT);s[st].font.size=Pt(sz);s[st].font.color.rgb=RGBColor.from_string(col)
 sec=d.sections[0];sec.top_margin=Inches(.55);sec.bottom_margin=Inches(.55);sec.left_margin=Inches(.58);sec.right_margin=Inches(.58)
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);run(p.add_run(title),25,True,NAVY)
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(p);run(p.add_run(sub),12,False,TEAL)
 hp=sec.header.paragraphs[0];hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT;bidi(hp);run(hp.add_run('تأسيس وعي المسلم المعاصر | الوحدة 3 v0.2'),8,True,TEAL)
 fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER;run(fp.add_run('إصدار إنتاجي v0.2  •  25 أكتوبر 2026'),8,False,MUTED)
 return d

def outputs():
 # facilitator
 d=doc('دليل الميسر','الوحدة 3 v0.2 | التاريخ والروابط والتطبيق المحدود')
 para(d,'وظيفة الوحدة','Heading 1',17,True);para(d,'نجاح الوحدة هو أن يستطيع المتعلم تسمية المصدر والنطاق والافتراض والحد، لا أن يخرج بحكم طائفي أو سياسي موحد. مواد أين الطريق عدسات معيارية متتبعة وليست برنامجاً لتنظيم الناس أو تقييمهم.')
 para(d,'اتفاق الحوار','Heading 2',13,True);bullets(d,['نتكلم عن رواية ومصدر وتفسير، لا «جوهر» جماعة.','لا طلب هوية أو موقف أو دفاع عن أسلاف.','حق المرور والحالة الافتراضية محفوظان.','لا تطبيق تاريخي على دولة/جماعة حاضرة ولا وصفة سياسية.','لا انتقاء أو تجنيد أو ولاء أو سلطة دينية.'])
 for n,w in WEEKS.items():
  para(d,f'الأسبوع {n} — {w["title"]}','Heading 1',17,True);para(d,'السؤال: '+w['question'],None,11,True,TEAL);tbl(d,['الوقت','التنفيذ'],w['agenda'],[1,5.9],8.5);para(d,'أسئلة ميسرة','Heading 2',13,True);bullets(d,QUESTIONS[n]);para(d,'تكييف المستويات','Heading 2',13,True);bullets(d,LEVELS[n]);para(d,'المواد والمخرج','Heading 2',13,True);tbl(d,['المادة الجديدة','المرافقة','النشاط','المخرج'],[(w['at'],w['other'],w['activities'],w['output'])],[1.8,1.8,1.5,1.8],7.7);para(d,'حاجز تشغيلي','Heading 2',13,True);para(d,w['guard'])
 para(d,'سجل بعد اللقاء','Heading 1',17,True);tbl(d,['سؤال','ملاحظة/قرار'],[('أين خلط المتعلمون واقعة برواية أو حكماً؟',''),('هل ظهرت شخصنة/طائفية/نخبوية؟ كيف أوقفت؟',''),('هل حفظت الحالة البديلة وحق المرور؟',''),('ما المصدر الذي يجب مراجعة أصله؟','')],[3.8,3.1],9);d.save(WORK/'01_facilitator_guide_module_03_v0_2.docx')
 # workbook
 d=doc('دفتر المتعلم','الوحدة 3 v0.2 | مصدر ونطاق وروابط وتطبيق محدود');para(d,'قاعدة الدفتر','Heading 1',17,True);para(d,'لا أكتب حكماً أكبر من دليلي، ولا أحول التاريخ إلى وصف لجماعة حاضرة أو مشروع للمستقبل.',None,11,True,TEAL)
 forms={9:[('خريطة شخص/فرصة/مؤسسة/سياق',['الحالة','الفاعل والفرصة','المؤسسة والسياق','دليل','قراءة بديلة','حد يمنع الحكم على الأشخاص']),('سلم الادعاء',['حالة ضيقة','دليل للتوسيع','حد']),],10:[('خط زمني متعدد المصادر',['الزمن','واقعة مزعومة','مصدر/رواية','تفسير','لايقين']),('محاكمة الادعاء',['الدعوى','النطاق','دليل','بديل','أثر اللغة','حد'])],11:[('خريطة نظم وروابط',['العلاقة','دليل أو افتراض','صوت غائب','حد']),('ميثاق جماعة تعلم',['قيمة','دور متناوب','قاعدة مصدر','اعتراض','مراجعة'])],12:[('الطبقات الأربع',['مبدأ','واقعة/مصدر','تفسير','تطبيق محدود','ما لا أستنبطه']),('بطاقة معرض',['شيء تحرك','مركزان/وسيط','دليل','بديل','حد'])]}
 for n,w in WEEKS.items():
  para(d,f'الأسبوع {n} | {w["title"]}','Heading 1',17,True);para(d,w['question'],None,11,True,TEAL)
  for title,fields in forms[n]:para(d,title,'Heading 2',13,True);tbl(d,['الحقل','ملاحظتي'],[(x,'\n\n') for x in fields],[2.6,4.3],9)
  para(d,'مراجعة: وضوح ___/5 | أمان السؤال/المرور ___/5 | عبء ___/5 | مصدر/حد ___/5',None,10,False,TEAL)
 d.save(WORK/'02_learner_workbook_module_03_v0_2.docx')
 # activities
 d=doc('بطاقات الأنشطة','C1–C8 | الوحدة 3 v0.2');cards=[('C1','خريطة فرصة وسياق','25','شخص/فرصة/مؤسسة/سياق/دليل/حد. لا انتقاء ولا هرمية.'),('C2','سلم الادعاء','15','من حالة ضيقة إلى تعميم؛ سمّ الدليل الإضافي والحد.'),('C3','خط زمني متعدد المصادر','25','واقعة/مصدر/تفسير/ذاكرة/سؤال مفتوح.'),('C4','محاكمة الادعاء لا الشخص','25','مصدر/نطاق/بديل/حد وحارس كرامة.'),('C5','خريطة النظم والروابط','30','عقد وأسهم مع دليل/افتراض وصوت غائب.'),('C6','ميثاق العلاقة والمراجعة','20','دور متناوب واعتراض ومراجعة؛ لا ولاء.'),('C7','معرض اتصال متعدد المراكز','25','شيء/مركزان/وسيط/دليل/حد.'),('C8','مبدأ إلى تطبيق محدود','18','طبقات أربع؛ لا مشروع حكم أو إقصاء.')]
 for c,t,tm,ins in cards:para(d,f'{c} | {t}','Heading 1',16,True,NAVY);para(d,f'الوقت: {tm} دقيقة',None,10,True,GOLD);para(d,ins);tbl(d,['قبل البدء','المخرج','حاجز'],[('حق المرور وحالة افتراضية','خريطة/بطاقة قابلة للتتبع','لا هوية/طائفية/ولاء/فعل سياسي')],[2.1,2.3,2.6],8.5)
 d.save(WORK/'03_activity_cards_module_03_v0_2.docx')
 res=list(csv.DictReader(open(SRC/'04_resource_registry_module_03_v0_2.csv',encoding='utf8')));gl=list(csv.DictReader(open(SRC/'05_glossary_module_03_v0_2.csv',encoding='utf8')))
 d=doc('سجل الموارد والمعجم','الوحدة 3 v0.2 | تتبع وحواجز');para(d,'قاعدة الاستعمال','Heading 1',17,True);para(d,'ورود المصدر لا يساوي توصية أو حسم. التاريخ الحساس يقرأ بمصدر ونطاق وبديل وحد؛ مواد أين الطريق منظور معياري متتبع لا برنامج سياسي أو تنظيمي.')
 tbl(d,['المعرّف','المادة','الدور','الحالة','الحاجز'],[(r['resource_id'],r['short_title'],r['week_or_role'],r['verification_status'],r['content_guardrail']) for r in res],[.8,1.7,1.7,1.3,1.7],6.3);para(d,'المعجم','Heading 1',17,True);tbl(d,['المصطلح','تعريف','الحد'],[(r['term_ar'],r['plain_definition'],r['boundary']) for r in gl],[1.4,3.5,2.3],7.5);d.save(WORK/'04_resource_registry_and_glossary_module_03_v0_2.docx')
 d=doc('التقويم وبروتوكول Pilot','الوحدة 3 v0.2 | فهم وأمان وتطبيق محدود');para(d,'المهمة الختامية','Heading 1',17,True);para(d,'خريطة تاريخية أو معرض صغير: مصدر، نطاق، تفسير/بديل، حد، ودرس مدني/تعليمي صغير. لا موقف طائفي أو سياسي ولا دعوة ولاء.')
 tbl(d,['المعيار','0','1','2','3'],[('مصدر ونطاق','غائب','عنوان','مناسب','مصدر/نطاق/حد'),('طبقات','خلط','طبقة','فصل','فصل وبديل'),('نظم/روابط','شخصنة','عامل واحد','عوامل','عوامل وصوت غائب'),('إنصاف','تعميم','قابل للتحسين','لغة منصفة','حد وأثر لغة'),('تطبيق','وصفة','غامض','محدود','محدود وقابل للإيقاف')],[1.3,1.2,1.2,1.2,1.9],8);para(d,'Pilot','Heading 1',17,True);para(d,'10–20 بالغاً، رمز منفصل، حق مرور، ولا تسجيلات. أي طائفية أو شخصنة أو دعوة ولاء أو استهداف علامة حمراء توقف النشاط. أخضر: 70%+ مصدر/نطاق/حد و80%+ أمان 4–5.')
 d.save(WORK/'05_assessment_and_pilot_module_03_v0_2.docx')
 # sheets
 def ws_init(ws,title,heads,rows,widths):
  ws.title=title;ws.sheet_view.rightToLeft=True;ws.freeze_panes='A2';ws.append(heads)
  for r in rows:ws.append(list(r))
  for c in ws[1]:c.fill=PatternFill('solid',fgColor=NAVY);c.font=Font(name=AR_FONT,bold=True,color=WHITE);c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
  for row in ws.iter_rows(min_row=2):
   for c in row:c.font=Font(name=AR_FONT,size=10,color=INK);c.alignment=Alignment(horizontal='right',vertical='top',wrap_text=True);c.border=Border(bottom=Side(style='hair',color='D9E2E8'));c.fill=PatternFill('solid',fgColor=LIGHT) if c.row%2==0 else PatternFill(fill_type=None)
  for i,w in enumerate(widths,1):ws.column_dimensions[chr(64+i)].width=w
  ws.row_dimensions[1].height=30;ws.auto_filter.ref=ws.dimensions
 wb=Workbook();ws=wb.active;ops=[]
 for n,w in WEEKS.items():
  for t,a in w['agenda']:ops.append((n,t,a,w['at'],w['output'],'مستكشف: قالب | ممارس: تطبيق محدود | متقدم: مصدر/بديل/حد'))
 ws_init(ws,'خريطة التشغيل',['الأسبوع','الوقت','الفقرة','المادة','المخرج','المسارات'],ops,[10,13,42,31,30,40]);s=wb.create_sheet();ws_init(s,'سجل الحواجز',['المجال','الخطر','الحاجز','الإجراء'],[('هوية','طائفية/شخصنة','حالة افتراضية ومصدر/نطاق','أوقف وأعد الصياغة'),('مؤهلات','نخبوية/انتقاء','قدرة ≠ قيمة شخص','ألغ التقييم'),('روابط','ولاء/سلطة','دور متناوب واعتراض','تصغير/إيقاف'),('تاريخ','وصفة سياسية','مبدأ/واقعة/تطبيق محدود','أجّل/أزل')],[18,34,35,25]);wb.save(WORK/'06_operations_map_module_03_v0_2.xlsx')
 wb=Workbook();ws=wb.active;ws_init(ws,'سجل الموارد',['المعرّف','العنوان','الدور','الموضع','الحالة','المخاطر','الحاجز'],[(r['resource_id'],r['short_title'],r['week_or_role'],r['source_locator'],r['verification_status'],r['claim_risk'],r['content_guardrail']) for r in res],[16,31,34,34,26,15,44]);s=wb.create_sheet();ws_init(s,'المعجم',['المصطلح','المقابل','التعريف','الحد','الأسبوع'],[(r['term_ar'],r['term_en_proposed'],r['plain_definition'],r['boundary'],r['week']) for r in gl],[20,24,50,42,13]);wb.save(WORK/'07_resource_registry_and_glossary_module_03_v0_2.xlsx')
 pilot=list(csv.reader(open(SRC/'08_pilot_data_template_module_03_v0_2.csv',encoding='utf8')));wb=Workbook();ws=wb.active;ws_init(ws,'متتبع Pilot',pilot[0],pilot[1:],[14,18,14,16,38,13,36,18,24]);s=wb.create_sheet();ws_init(s,'لوحة قرار',['المؤشر','الهدف','القيمة','القرار'],[('مصدر/نطاق/حد','70%+','',''),('أمان المرور','80%+ 4–5','',''),('طائفية/شخصنة','0','','أوقف/أعد التصميم'),('دعوة ولاء','0','','أوقف/إحالة'),('أمان أقل من 60%','0','','أوقف النشاط')],[32,18,14,30]);wb.save(WORK/'08_pilot_tracker_module_03_v0_2.xlsx')

def ppt_text(shape,text,size=18,bold=False,color=INK,align=PP_ALIGN.RIGHT):
 tf=shape.text_frame;tf.clear();tf.word_wrap=True;tf.margin_left=PInches(.12);tf.margin_right=PInches(.12);tf.margin_top=PInches(.06);tf.vertical_anchor=MSO_ANCHOR.MIDDLE;p=tf.paragraphs[0];p.alignment=align;pr=p._p.get_or_add_pPr();b=OxmlElement('a:bidi');b.set('val','1');pr.append(b);r=p.add_run();r.text=str(text);r.font.name=AR_FONT;r.font.size=PPt(size);r.font.bold=bold;r.font.color.rgb=PRGB.from_string(color)
def box(s,x,y,w,h,text,fill=WHITE,line='D5E3E7',size=18,bold=False,color=INK,rounded=True):
 sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,PInches(x),PInches(y),PInches(w),PInches(h));sh.fill.solid();sh.fill.fore_color.rgb=PRGB.from_string(fill);sh.line.color.rgb=PRGB.from_string(line);ppt_text(sh,text,size,bold,color);return sh
def head(s,w,t,sub=''):
 sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,PInches(13.333),PInches(.6));sh.fill.solid();sh.fill.fore_color.rgb=PRGB.from_string(NAVY);sh.line.fill.background();box(s,.45,.1,12.4,.32,f'الوحدة 3 v0.2 | الأسبوع {w}',NAVY,NAVY,11,True,WHITE,False);box(s,.55,.8,12.1,.55,t,WHITE,WHITE,24,True,NAVY,False)
 if sub:box(s,.62,1.38,11.8,.35,sub,WHITE,WHITE,13,False,TEAL,False)
def deck(n):
 w=WEEKS[n];p=Presentation();p.slide_width=PInches(13.333);p.slide_height=PInches(7.5);blank=p.slide_layouts[6];ss=[]
 s=p.slides.add_slide(blank);head(s,n,w['title'],w['question']);box(s,.85,2.0,11.6,1.15,w['output'],PALE,PALE,21,True,NAVY);box(s,1.2,3.7,10.9,.8,'المعيار: مصدر ونطاق وحد وكرامة، لا هوية أو ولاء أو وصفة سياسية.',LIGHT,LIGHT,17,False,INK);ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'خريطة اللقاء','تحضير موجّه + لقاء حي + تطبيق محدود');a='\n'.join(f'{x} | {y}' for x,y in w['agenda'][:4]);b='\n'.join(f'{x} | {y}' for x,y in w['agenda'][4:]);box(s,.65,1.95,5.9,3.8,a,WHITE,'C8DDE1',15);box(s,6.8,1.95,5.9,3.8,b,WHITE,'C8DDE1',15);box(s,1.0,6.05,11.3,.55,'حق المرور والحالة الافتراضية والكتابة البديلة محفوظة.',PALE,PALE,15,True,TEAL);ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'من رواية إلى تعلم مسؤول');keys=['واقعة/ادعاء','مصدر/موضع','تفسير/افتراض','بديل','حد وتطبيق محدود']
 for i,x in enumerate(keys):box(s,.55+i*2.48,2.35,2.08,1.35,x,PALE if i%2==0 else LIGHT,PALE if i%2==0 else 'DDE5EB',16,True,NAVY if i%2==0 else INK)
 box(s,1.05,4.75,11.1,.72,'لا يتحول المصدر إلى حكم على هوية، ولا يتحول التاريخ إلى برنامج حاضر.',WHITE,GOLD,19,True,GOLD);ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'المصدر وحده لا يكفي');box(s,.75,1.9,5.9,3.3,'المادة الجديدة\n'+w['at']+'\n\nوظيفتها: عدسة وسؤال ولغة تحتاج تحليلاً.',LIGHT,'DDE5EB',17,True,NAVY);box(s,6.75,1.9,5.9,3.3,'حاجز الاستعمال\nراجع الأصل.\nسمّ المصدر والنطاق.\nأضف البديل والحد.',PALE,PALE,17,True,TEAL);box(s,1.1,5.7,11.1,.5,w['guard'],WHITE,RED,13,True,RED);ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'الورشة الحية: '+w['activities']);steps={9:['1. ارسم شخصاً وفرصة وسياقاً.','2. سمّ الدليل والبديل.','3. اكتب ما لا تحكم به.'],10:['1. افصل واقعة/رواية/تفسير.','2. سمّ المصدر والنطاق.','3. اكتب حداً وأثر اللغة.'],11:['1. ارسم أدواراً لا أشخاصاً ثابتين.','2. ضع دليلاً أو افتراضاً.','3. أضف اعتراضاً ومراجعة.'],12:['1. افصل الطبقات الأربع.','2. سمّ الدليل والبديل.','3. صمم تطبيقاً محدوداً.']}[n]
 for i,x in enumerate(steps):box(s,1.0,2.05+i*1.3,11.2,.88,x,PALE if i==1 else WHITE,TEAL if i==1 else 'DDE5EB',19,i==1,NAVY)
 ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'المسارات الثلاثة');labels=[('مستكشف 18–30','قالب واضح وحالة افتراضية ومهارة واحدة.'),('ممارس عام','تطبيق مدني/تعليمي قريب من الحياة بلا إفصاح.'),('باحث/معلّم','مصدران وبديل وحد وملاحظة عن الحاجز.')]
 for i,(a,b) in enumerate(labels):box(s,.72+i*4.18,2.0,3.75,3.25,a+'\n\n'+b,PALE if i==1 else LIGHT,TEAL if i==1 else 'DDE5EB',17,True,NAVY if i==1 else INK)
 box(s,1.0,5.85,11.2,.5,'عمق مختلف، وكرامة متساوية، ولا ترتيب للأشخاص أو الانتماءات.',WHITE,GOLD,15,True,GOLD);ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'ما الذي سنلاحظه؟');e={9:'شخص/فرصة/سياق/حد بلا نخبوية.',10:'واقعة/مصدر/تفسير/حد بلا طائفية.',11:'دور/قاعدة/اعتراض بلا ولاء.',12:'مبدأ/واقعة/تطبيق محدود بلا وصفة حكم.'}[n];box(s,.75,1.9,11.8,1.0,e,PALE,PALE,21,True,NAVY);box(s,.75,3.3,3.65,2.1,'وضوح\nهل سميت المصدر؟',LIGHT,'DDE5EB',19,True,INK);box(s,4.82,3.3,3.65,2.1,'أمان\nهل أستطيع المرور؟',PALE,PALE,19,True,TEAL);box(s,8.9,3.3,3.65,2.1,'حد\nهل منعت التعميم؟',LIGHT,'DDE5EB',19,True,INK);ss.append(s)
 s=p.slides.add_slide(blank);head(s,n,'قبل أن نغادر');prompts={9:['قدرة لن أحولها إلى قيمة شخص','مصدر سأطلبه','حد سأصرح به'],10:['رواية سأفصلها عن واقعة','قراءة سأُنصفها','تسمية سأجنبها'],11:['قاعدة تحمي الكرامة','اعتراض سأحميه','دور سأدوّره'],12:['مبدأ سأميزه','تطبيق صغير محدود','ما لن أستنبطه']}[n]
 for i,x in enumerate(prompts):box(s,.85,1.8+i*1.25,11.6,.8,x+'  ______________________________________________',WHITE,'C8DDE1',18,False,NAVY)
 box(s,1.35,5.9,10.65,.62,'تعلم تاريخي مسؤول: مصدر، نطاق، بديل، حد، وكرامة.',NAVY,NAVY,18,True,WHITE);ss.append(s)
 for i,s in enumerate(ss,1):box(s,.45,7.1,12.4,.18,f'تأسيس وعي المسلم المعاصر  •  إصدار v0.2  •  {i}/8',WHITE,WHITE,8,False,MUTED,False)
 assert len(ss)==8;p.save(WORK/f'{n+1:02d}_week_{n}_meeting_slides_module_03_v0_2.pptx')

def final():
 wt(FINAL/'README_module_03_v0_2.md','''# الحزمة النهائية — الوحدة 3 v0.2

## التاريخ والروابط والتطبيق المحدود

إعادة بناء الأسابيع 9–12 بعد إدخال AT-03 وAT-09 وAT-13 كمواد أولية متتبعة. لا تستبدل v0.1.

- قدرة/فرصة/مؤسسة/سياق بلا نخبوية.
- تاريخ حساس بمصدر ونطاق وحد بلا طائفية أو شخصنة.
- روابط وجماعة تعلم بلا ولاء أو سلطة.
- مبدأ/واقعة/تفسير/تطبيق محدود بلا مشروع حكم أو إقصاء.

التوزيع: 9 أصول نصية، 5 DOCX، 3 XLSX، 4 PPTX (8 شرائح لكل عرض).
''')
 checks=[]
 def chk(a,b,c):checks.append((a,b,c))
 for f in sorted(WORK.glob('*.docx')):
  try:d=Document(f);chk(f.name,bool('\n'.join(p.text for p in d.paragraphs).strip()),f'{len(d.paragraphs)} paragraphs; {len(d.tables)} tables')
  except Exception as e:chk(f.name,False,str(e))
 for f in sorted(WORK.glob('*.xlsx')):
  try:w=load_workbook(f,read_only=True);chk(f.name,len(w.sheetnames)>=1,f'{len(w.sheetnames)} worksheets')
  except Exception as e:chk(f.name,False,str(e))
 for f in sorted(WORK.glob('*.pptx')):
  try:p=Presentation(f);chk(f.name,len(p.slides)==8,f'{len(p.slides)} slides (required 8)')
  except Exception as e:chk(f.name,False,str(e))
 sf=sorted(SRC.iterdir());chk('source_asset_count',len(sf)==9,f'{len(sf)} source assets (required 9)');chk('production_output_count',len(list(WORK.iterdir()))==12,f'{len(list(WORK.iterdir()))} production outputs (required 12)')
 def report(withzip=False):
  x=['# تقرير تحقق — الوحدة 3 v0.2','','تاريخ التشغيل: 2026-10-25','','| العنصر | النتيجة | التفاصيل |','|---|---|---|']+[f'| `{a}` | {"PASS" if b else "FAIL"} | {c} |' for a,b,c in checks]+['','## مراجعة تحريرية','- AT-03/AT-09/AT-13 مواد أولية متتبعة، لا أدوات انتقاء أو ولاء أو مشروع حكم.','- حواجز ضد الطائفية والشخصنة والنخبوية والقياس التاريخي المباشر ظاهرة في المخرجات.','- لا اختبار هوية أو اعتقاد، ولا تجنيد أو سلطة دينية أو فعل تعبوي.',''];return '\n'.join(x)
 wt(FINAL/'validation_report_module_03_v0_2.md',report())
 def zipit():
  if ZIP.exists():ZIP.unlink()
  with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   z.write(FINAL/'README_module_03_v0_2.md','03_final_package/README_module_03_v0_2.md');z.write(FINAL/'validation_report_module_03_v0_2.md','03_final_package/validation_report_module_03_v0_2.md')
   for f in sf:z.write(f,'01_source_text_assets/'+f.name)
   for f in sorted(WORK.iterdir()):z.write(f,'02_working_outputs/'+f.name)
 zipit()
 with zipfile.ZipFile(ZIP) as z:chk('final_zip_integrity',z.testzip() is None,f'{len(z.namelist())} entries');chk('final_zip_entry_count',len(z.namelist())==23,f'{len(z.namelist())} entries (required 23)')
 wt(FINAL/'validation_report_module_03_v0_2.md',report());zipit()
 with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None and len(z.namelist())==23
 return checks

def main():
 clean();sources();outputs()
 for n in WEEKS:deck(n)
 c=final();print(json.dumps({'root':str(OUTROOT),'source_assets':len(list(SRC.iterdir())),'outputs':len(list(WORK.iterdir())),'zip':str(ZIP),'entries':len(zipfile.ZipFile(ZIP).namelist()),'md5':hashlib.md5(ZIP.read_bytes()).hexdigest(),'checks':c},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
