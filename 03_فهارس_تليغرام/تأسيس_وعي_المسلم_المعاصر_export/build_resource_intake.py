from pathlib import Path
import json, csv, re
from urllib.parse import urlparse, urlunparse
from collections import Counter
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'deliverables'
OUT.mkdir(exist_ok=True)
msgs=json.loads((ROOT/'messages_parsed.json').read_text(encoding='utf-8'))

# Telegram export has a stable local post identifier (messageNNN).
# The source channel uses t.me/islamic_b2/NNN for its own index pointers.
def canonical_url(url):
    p=urlparse(url.strip())
    if not p.scheme: return url.strip()
    # tracking strings are retained in source context but omitted in dedupe identity.
    return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'',p.query,'')).rstrip('/')

def internal_index_link(url):
    p=urlparse(url)
    return p.netloc.lower() in {'t.me','telegram.me'} and p.path.strip('/').startswith('islamic_b2/')

def media_kind(media):
    n=media['name'].lower()
    if re.search(r'\.(pdf|epub|mobi|azw3?|djvu)$', n): return 'book_or_document_file'
    if re.search(r'\.(mp3|m4a|wav|ogg)$', n): return 'audio_file'
    if re.search(r'\.(mp4|mkv|avi|mov)$', n): return 'video_file'
    return 'file_or_media'

def link_kind(url, label, text):
    host=urlparse(url).netloc.lower()
    s=' '.join([url,label,text]).lower()
    if 'youtube' in host or 'youtu.be' in host: return 'video_or_playlist'
    if 'coursera' in host: return 'course'
    if 'drive.google' in host: return 'drive_resource'
    if 't.me' in host: return 'telegram_resource'
    if 'shamela' in host: return 'digital_library_record'
    if any(x in s for x in ['.pdf','.epub','.mobi','.azw']): return 'book_or_document_link'
    return 'web_resource'

def candidate_modules(text, hashtags):
    s=' '.join([text,hashtags])
    hits=[]
    # labels are candidate placements, not endorsements
    if any(t in s for t in ['كيف_أتعلم','تعلم','القراءة','كتابة علمية','بحث علمي','منهج','مصطلح التاريخ','مفهوم التاريخ','تفكير','فلسفة العلم','طغيان العلم','الوعي']):
        hits.append('U1: learning how to know')
    if any(t in s for t in ['سيرة','مكي','جذور','قرآن','رسالة']):
        hits.append('U2: meaning/message/early community')
    if any(t in s for t in ['خلفاء','فتنة','أموي','عباسي','مذاهب','المحدثين']):
        hits.append('U3: early history/power/belonging')
    if any(t in s for t in ['عثماني','تاريخ المجتمعات','صلاح الدين','صهيوني','دولة','إصلاح سياسي']):
        hits.append('U4: power/weakness/transformation')
    if any(t in s for t in ['استعمار','إسرائيل','فلسطين','حداثة','علمانية','لغة','شبكات']):
        hits.append('U5: modernity/colonialism/identity')
    if any(t in s for t in ['علم','فيزياء','كوانتم','فلسفة العلم','تطور','مستقبل']):
        hits.append('U6: science/modern world/responsible action')
    return ' | '.join(dict.fromkeys(hits)) or 'editorial review needed'

def priority_flag(message_id, text):
    # Manually reviewed high-value candidates for the agreed course; does not equal assignment.
    mids={
        'message29','message368','message393','message395','message404','message411','message412','message414','message415',
        'message421','message433','message445','message461','message469','message489','message510','message535','message546','message613'
    }
    if message_id in mids: return 'priority review queue'
    return 'full inventory / editorial triage'

# Candidate resource card = an attachment OR a direct external resource link. Internal index pointers are logged separately
# in raw inventory; they are not falsely treated as independent learning resources.
records=[]
for msg in msgs:
    mid=msg['message_id']; text=msg['text']; tags=' | '.join(msg['hashtags'])
    for media in msg['media']:
        if not media['name'] or media['name'].strip().lower()=='photo':
            continue
        records.append({
            'resource_id':'', 'source_kind':'attached_media_mentioned_in_export','resource_type':media_kind(media),
            'candidate_title':media['name'], 'creator_or_org_as_stated':'', 'direct_url':'',
            'source_message':mid,'source_datetime':msg['timestamp'],'source_context':text,
            'hashtags':tags,'media_status':media['status'], 'candidate_course_placement':candidate_modules(text+' '+media['name'],tags),
            'triage':priority_flag(mid,text), 'verification_status':'mentioned in Telegram export — bibliographic verification required',
            'rights_access_note':'No file content was downloaded or redistributed. Confirm lawful access, edition, licence and suitability before assignment.'
        })
    for link in msg['links']:
        url=link['url'].strip()
        if not url or internal_index_link(url):
            continue
        # stable duplicate key in source list; labels are retained as given in export.
        records.append({
            'resource_id':'', 'source_kind':'direct_link_mentioned_in_export','resource_type':link_kind(url,link['label'],text),
            'candidate_title':link['label'] or url, 'creator_or_org_as_stated':'', 'direct_url':url,
            'source_message':mid,'source_datetime':msg['timestamp'],'source_context':text,
            'hashtags':tags,'media_status':'', 'candidate_course_placement':candidate_modules(text+' '+link['label'],tags),
            'triage':priority_flag(mid,text), 'verification_status':'link captured from Telegram export — bibliographic verification required',
            'rights_access_note':'Verify current availability, lawful access, author/organisation and version before assignment or redistribution.'
        })

# exact resource identity: attachment filename or canonical direct URL
seen={}
for r in records:
    key=('media:'+re.sub(r'\s+',' ',r['candidate_title'].strip().lower())) if r['source_kind'].startswith('attached') else ('url:'+canonical_url(r['direct_url']))
    if key not in seen:
        r['source_messages']=r['source_message']; r['occurrences']=1; seen[key]=r
    else:
        prior=seen[key]; prior['occurrences']+=1
        prior['source_messages']+=' | '+r['source_message']
        if r['source_message'] in {
            'message29','message368','message393','message395','message404','message411','message412','message414','message415','message421','message433','message445','message461','message469','message489','message510','message535','message546','message613'
        }:
            prior['triage']='priority review queue'

records=list(seen.values())
for idx,r in enumerate(sorted(records,key=lambda x:(x['triage']!='priority review queue',x['candidate_title'].lower())),1):
    r['resource_id']=f'TG-WA3Y-{idx:04d}'
records=sorted(records,key=lambda x:x['resource_id'])
fields=['resource_id','source_kind','resource_type','candidate_title','creator_or_org_as_stated','direct_url','source_message','source_messages','source_datetime','source_context','hashtags','media_status','candidate_course_placement','triage','verification_status','rights_access_note','occurrences']
with (OUT/'01_full_resource_inventory_v0_1.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)

# Selected expert/editor review queue: records from manually inspected source posts, preserving evidence but no endorsement.
priority=[r for r in records if r['triage']=='priority review queue']
with (OUT/'02_priority_review_queue_v0_1.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(priority)

# Build a high-level audit report
cats=Counter(x['resource_type'] for x in records)
raw_internal=sum(1 for m in msgs for a in m['links'] if internal_index_link(a['url']))
md=f'''# استقبال وتفريغ موارد Telegram — قناة «ترشيحات معلمي الناس الخير 📘»

## المصدر والنطاق

- **مجلد المصدر:** `ChatExport_2026-10-22` في Google Drive، كما شاركه المستخدم.
- **الملف المفحوص:** `messages.html`، بامتداد 771,105 بايت.
- **محتوى التصدير:** قناة باسم «ترشيحات معلمي الناس الخير 📘»؛ لا يظهر في التصدير أنه حوار البوت نفسه.
- **قاعدة الاختيار المتفق عليها:** نلتقط فقط الموارد التي نُشرت أو رُبطت صراحة في التصدير، لا نُنشئ توصيات من خارج المصدر.

## ما استخرجناه

| البند | العدد |
|---|---:|
| رسائل تحتوي نصاً أو مرفقاً أو رابطاً | {len(msgs)} |
| مؤشرات Telegram الداخلية (فهارس تقود إلى منشورات داخل القناة) | {raw_internal} |
| سجلات مورد مستقلة بعد استبعاد مؤشرات الفهرسة الداخلية ودمج التكرارات الدقيقة | {len(records)} |
| سجلات في قائمة المراجعة ذات الأولوية | {len(priority)} |
| مرفقات/كتب أو وثائق مسماة | {sum(1 for x in records if x['source_kind'].startswith('attached'))} |
| روابط مباشرة خارج فهرس القناة | {sum(1 for x in records if x['source_kind'].startswith('direct'))} |

### أنواع السجلات

| النوع | العدد |
|---|---:|
'''
for k,v in sorted(cats.items()): md+=f'| `{k}` | {v} |\n'
md+='''
## كيف تستخدم الملفات

- `01_full_resource_inventory_v0_1.csv/.xlsx`: السجل الكامل القابل للفرز. كل صف يحمل عنواناً كما ورد، ومنشور الدليل، والسياق، والرابط إن وجد، وحالة تحقق صريحة.
- `02_priority_review_queue_v0_1.csv/.xlsx`: قائمة أصغر لموارد تبدو واعدة مباشرة للدورة أو لمعيار مصادرها. **القائمة ليست قراءة مقررة بعد.**
- `03_module_placement_shortlist.md`: قرار تحريري أولي: ما الذي يمكن مراجعته أولاً للوحدة 1، وما الذي يؤجل إلى الوحدات اللاحقة.
- `message_inventory.csv` و`resource_candidates_raw_deduplicated.csv`: أثر تدقيقي خام من التصدير؛ لا تستخدمهما كسجل ببليوغرافي نهائي.

## حد مهم للحقوق والجودة

التصدير يذكر أسماء  ملفات وروابط، لكنه لم يشمل محتوى معظم الكتب/الوثائق (`Not included, change data exporting settings to download`). لم ننزّل أو نعد توزيع أي كتاب أو PDF أو ملف من القناة أو من روابطها. لذلك:

1. لا يُعامل ظهور مورد في القناة كتوصية من هذه الدورة.
2. لا يُضاف مورد إلى قراءات المتعلمين قبل تثبيت العنوان والمؤلف والطبعة/الناشر والرابط القانوني ومدى صلته بناتج التعلم.
3. الموارد العقدية والفقهية والسياسية والتاريخية المتنازع عليها تُحال لمراجع مجال متخصص قبل التكليف بها.
4. نفضّل روابط الناشر/المؤسسة أو المكتبة القانونية على نسخ الملفات غير الواضحة الحقوق.
'''
(OUT/'00_export_audit_and_usage.md').write_text(md,encoding='utf-8')

short='''# قائمة وضع تحريري أولية — موارد مرشحة من تصدير Telegram

> هذه ليست قائمة قراءة نهائية. كل مورد هنا **ورد صراحة في التصدير**، واختير للمراجعة أولاً لأنه يخدم أسئلة الدورة، ثم يوضع في السجل بالحالة المناسبة بعد التحقق.

## أ. مرشحات مراجعة فورية للوحدة 1: تعلّم كيف نعرف

| المورد كما ورد | الدليل في التصدير | الاستعمال المقترح | القرار الحالي |
|---|---|---|---|
| **Learning How to Learn** (Coursera) | `message29`، رابط Coursera | تحضير ذاتي اختياري حول الاسترجاع والممارسة وإدارة التعلم. | تحقق من اللغة والإتاحة الحالية؛ لا يجعل شرطاً أساسياً. |
| **Open Syllabus** | `message368` | أداة للباحث/الميسر للعثور على مناهج جامعية ومقارنة قوائم قراءة. | أداة تصميم، لا مصدر محتوى موثوق وحده. |
| **MIT Challenge / Scott H. Young** | `message393` | مثال لتقسيم المحاضرات وتلخيصها؛ يفيد في دفتر التعلم. | تحقق من المقال الأصلي؛ لا يقدم كدليل على فاعلية عامة بلا مراجعة. |
| **سلسلة مقدمة قصيرة جداً** (هنداوي) | `message395` | قراءة تمهيدية مختارة حسب الموضوع، لا إحالة عامة للسلسلة كلها. | سجّل كل عنوان على حدة قبل التكليف. |
| **Project: Writing a Research Paper** (Coursera) | `message404` | امتداد اختياري للمسار المتقدم، وخصوصاً مشروع التخرج. | يراجع لاحقاً للوحدة 6/المشروع. |
| **الدليل للكتابة العلمية باللغة العربية — ج1 وج2** | `message411–412` | دعم للباحثين في توثيق وكتابة المذكرات. | ثبّت المؤلف والناشر والطبعة والرخصة قبل الاستخدام. |
| **أساسيات البحث العلمي — علماء مصر** | `message414` مع رابط المصدر | تمهيد اختياري لمهام السؤال والمصدر والتوثيق. | راجع النسخة الرسمية وتاريخها قبل الإدراج. |
| **خصائص الكتابة العلمية باللغة العربية** | `message415` | إثراء للمسار المتقدم. | يحتاج بيانات ببليوغرافية. |
| **كيف يتعلم الناس** | `message445` | مرجع تصميم للميسر، لا قراءة لازمة للمتعلم. | حدّد بدقة أي طبعة/ترجمة قبل إدراجه؛ لا تعتمد نسخة مرفقة غير مثبتة. |
| **التفكير السريع والبطيء — دانيال كانمان** | `message461` | إثراء محدود عن الاختصارات الذهنية والانحياز؛ مع تحذير من تبسيط العلم النفسي. | تحقق من الطبعة والترجمة، ولا تستخدمه لتعميمات تشخيصية. |
| **مصطلح التاريخ — أسد رستم** | `message433` | مسار متقدم للمصدر والتاريخ، خصوصاً وحدتي 1 و3. | مراجعة خبير تاريخ/منهج، وتثبيت الطبعة. |
| **مفهوم التاريخ — عبدالله العروي** | `message613` | قراءة متقدمة في فلسفة التاريخ ومنهج المفهوم، لا مدخل للمبتدئ. | تحقق ببليوغرافي ومراجعة ملاءمة قبل التكليف. |
| **برنامج برة الصندوق: التفكير/اللغة/قراءة التاريخ** | `message489` | مقاطع انتقائية محتملة للوحدات 1 و3 و5 بعد مراجعة الطابع الزمني وحقوق النشر. | لا يضاف إلا ببطاقات Chunk مستقلة ومصادر موازنة. |
| **تفريغ/ملخص إعادة تأسيس وعي المسلم المعاصر 1** | `message535` و`message546` | مساعد لمقارنة المواضع مع مجموعة تفريغات أيمن الموجودة لدينا. | مصدر مساعد فقط؛ يراجع مقابلة بالفيديو الأصلي قبل اقتباسه. |

## ب. مرشحات للوحدة 6: العلم والعالم الحديث

| المورد كما ورد | الدليل | الاستخدام المحدود المقترح | الحاجز قبل الاستخدام |
|---|---|---|---|
| فلسفة العلم في القرن العشرين — يمنى طريف الخولي | `message421` | إثراء للميسر حول التفريق بين العلم والفلسفة. | تثبيت الطبعة ومراجعة متخصص في فلسفة العلم. |
| الفيزياء والفلسفة: ثورة في العلم — فيرنر هايزنبرغ | `message428` | قراءة تاريخية/فلسفية متقدمة، لا برهان علمي على دعوى عقدية. | التحقق من الترجمة والطبعة وسياق الكتاب. |
| طغيان العلم — بول فييرابند | `message469` | قراءة خلافية حول حدود العلم؛ يوازَن بقراءات أخرى. | لا يقدّم بوصفه موقفاً محسوماً؛ يحتاج ميسر متخصص. |

## ج. مسار مادة/تحقق يحتاجان عناية خاصة

- الموارد المعنونة بملفات PDF/EPUB في التصدير: **562 سجلاً فريداً**. تحفظ كبيانات وصفية فقط، ولا يجري تنزيلها جماعياً أو توزيعها.
- روابط القناة الداخلية ليست مورداً مستقلاً؛ حُفظت في الأثر التدقيقي لتتبع الفهارس فقط.
- روابط Drive وYouTube والقنوات الأخرى تعطي نقطة بداية للوصول، لا دليلاً على ثبات الرابط أو صحة المحتوى أو قانونية إعادة النشر.

## بروتوكول إدراج مورد من هذه القائمة

1. اقرأ الصفحة الأصلية أو النسخة القانونية، لا اسم الملف فقط.
2. ثبّت: المؤلف/الجهة، العنوان، الطبعة أو التاريخ، الناشر، والرابط الثابت.
3. صنّف الادعاءات التي سيُستخدم المورد من أجلها: تاريخية/علمية/فلسفية/أخلاقية/سياسية.
4. حدد ناتج تعلم واحداً وموضعاً محدداً؛ لا تعيّن كتاباً كاملاً بلا سبب.
5. دوّن بديلًا أو قيداً عندما تكون المادة خلافية أو تفسيرية.
6. حدّث السجل المركزي: مذكور → متحقق ببليوغرافياً → مقرر/إثرائي، أو يستبعد مع السبب.
'''
(OUT/'03_module_placement_shortlist.md').write_text(short,encoding='utf-8')

# XLSX publication of the two CSV registers.
def to_xlsx(records, name, sheet):
    wb=Workbook(); ws=wb.active; ws.title=sheet
    ws.append(fields)
    for r in records: ws.append([r.get(x,'') for x in fields])
    fill=PatternFill('solid',fgColor='13293D'); thin=Side(style='thin',color='D6DEE3')
    for c in ws[1]:
        c.fill=fill;c.font=Font(name='Arial',color='FFFFFF',bold=True);c.alignment=Alignment(horizontal='right',vertical='center',wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font=Font(name='Arial',size=10);c.alignment=Alignment(horizontal='right',vertical='top',wrap_text=True);c.border=Border(bottom=thin)
    ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions;ws.row_dimensions[1].height=35
    for i,col in enumerate(ws.columns,1):
        letter=get_column_letter(i);maxl=max(len(str(c.value or '')) for c in col)
        ws.column_dimensions[letter].width=min(max(maxl*.72,12),50)
    if ws.max_row>1:
        tab=Table(displayName='ResourceTable',ref=f'A1:{get_column_letter(ws.max_column)}{ws.max_row}')
        tab.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showFirstColumn=False,showLastColumn=False,showRowStripes=True,showColumnStripes=False)
        ws.add_table(tab)
    wb.save(OUT/name)

to_xlsx(records,'01_full_resource_inventory_v0_1.xlsx','Full Inventory')
to_xlsx(priority,'02_priority_review_queue_v0_1.xlsx','Priority Review')
print(f'Wrote {len(records)} full records, {len(priority)} priority records')
