from pathlib import Path
import json, csv, re
from collections import Counter, defaultdict
from urllib.parse import urlparse, urlunparse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'course_resource_index'
OUT.mkdir(exist_ok=True)
msgs=json.loads((ROOT/'messages_parsed.json').read_text(encoding='utf-8'))
by_id={m['message_id']:m for m in msgs}

SELF_CHANNELS={'almuslimalmueasir1'}
BOT_CHANNELS={'wa3y_bot'}

def parse_telegram_target(url):
    p=urlparse(url)
    if p.netloc.lower() not in {'t.me','telegram.me'}: return None
    parts=p.path.strip('/').split('/')
    if len(parts)>=2 and parts[1].isdigit(): return parts[0].lower(), int(parts[1])
    return None

def normalize_url(url):
    p=urlparse(url)
    return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'',p.query,'')).rstrip('/') if p.scheme else url

def clean(s): return re.sub(r'\s+',' ',s.replace('\u2068','').replace('\u2069','')).strip()

def media_type(n):
    n=n.lower()
    if re.search(r'\.(pdf|epub|mobi|azw3?|djvu)$',n): return 'book_or_document_file'
    if re.search(r'\.(mp3|m4a|wav|ogg)$',n): return 'audio_file'
    if re.search(r'\.(mp4|mkv|avi|mov)$',n): return 'video_file'
    return 'file_or_media'

def direct_type(u):
    h=urlparse(u).netloc.lower()
    if 'youtube' in h or 'youtu.be' in h: return 'video_or_playlist'
    if 'soundcloud' in h: return 'audio_or_playlist'
    if 'coursera' in h: return 'course'
    if 'archive.org' in h: return 'digital_archive_record'
    if 't.me' in h: return 'external_telegram_resource'
    return 'web_resource'

def candidate_module_from_lesson(label):
    # Mapping is a tentative editorial bridge to the separate 24-week course architecture.
    # It does NOT transform original-course recommendations into assigned readings.
    s=label
    if 'الجزء الثاني' in s: return 'U2–U5: specialised/sensitive religious-history material — subject-expert review'
    if any(x in s for x in ['الدرس الأول','الدرس الاول']): return 'U1: learning how to know'
    if any(x in s for x in ['الدرس الثاني','الدرس الثالث']): return 'U1–U3: methods, history and early community — expert review'
    if any(x in s for x in ['الدرس الرابع','الدرس الخامس','الدرس السادس','الدرس السابع','الدرس الثامن','الدرس التاسع','الدرس العاشر','الدرس الحادي عشر','الدرس الثاني عشر','الدرس الثالث عشر']): return 'U3–U5: history, institutions, colonialism and identity — expert review'
    return 'editorial review needed'

def risk_from_title_and_lesson(title,lesson):
    s=(title+' '+lesson)
    high=['الجهاد','قتال','شيع','تكفير','الطوائف','الفتنة','قتال','السلفية','اللامذهبية','الجهمية','البدع','منهاج السنة','إسرائيل','فلسطين','العلمانية']
    medium=['استعمار','الدولة','سياسي','حزب','تاريخ','عثمان','صفوي','مذاهب','استبداد','الجيش']
    if any(x in s for x in high): return 'high: specialist review required'
    if any(x in s for x in medium): return 'medium: context and multiple-source check required'
    return 'standard: bibliographic and pedagogical review required'

# Master resources: named attachments and direct non-self links. Name-only references remain traceable in message inventory.
master=[]
for m in msgs:
    for md in m['media']:
        name=clean(md['name'])
        if not name or name.lower()=='photo': continue
        master.append({
            'resource_id':'','source_kind':'attached_media_mentioned_in_export','resource_type':media_type(name),
            'candidate_title':name,'direct_url':'','source_message':m['message_id'],'source_datetime':m['timestamp'],
            'source_context':clean(m['text']),'media_status':md['status'],'verification_status':'mentioned in Telegram export — bibliographic verification required',
            'rights_access_note':'No file content downloaded or redistributed. Verify legal access, complete bibliographic data and suitability before assignment.'
        })
    for a in m['links']:
        u=a['url'].strip(); target=parse_telegram_target(u)
        if target and target[0] in SELF_CHANNELS | BOT_CHANNELS: continue
        # Skip empty and log all other direct links, even if label is generic.
        if not u: continue
        master.append({
            'resource_id':'','source_kind':'direct_link_mentioned_in_export','resource_type':direct_type(u),
            'candidate_title':clean(a['label']) or u,'direct_url':u,'source_message':m['message_id'],'source_datetime':m['timestamp'],
            'source_context':clean(m['text']),'media_status':'','verification_status':'link captured from Telegram export — bibliographic verification required',
            'rights_access_note':'Verify current availability, lawful access, author/organisation and version before assignment or redistribution.'
        })

# exact dedupe by media name or URL
unique={}
for r in master:
    key='media:'+r['candidate_title'].lower() if r['source_kind'].startswith('attached') else 'url:'+normalize_url(r['direct_url'])
    if key not in unique:
        r['source_messages']=r['source_message'];r['occurrences']=1;unique[key]=r
    else:
        p=unique[key];p['occurrences']+=1;p['source_messages']+=' | '+r['source_message']
master=list(unique.values())
master.sort(key=lambda x:(x['resource_type'],x['candidate_title'].lower()))
for i,r in enumerate(master,1): r['resource_id']=f'AYMAN-TG-{i:04d}'
resource_by_key={('media:'+r['candidate_title'].lower() if r['source_kind'].startswith('attached') else 'url:'+normalize_url(r['direct_url'])):r for r in master}

# Lesson catalogue: use late compiled posts rather than every repeated posting.
# Preserve all items but consolidate duplicate labels by the normalized lesson title.
lesson_headers=[]
for m in msgs:
    num=int(re.search(r'\d+',m['message_id']).group())
    txt=clean(m['text'])
    if num>=1036 and re.match(r'^(الدرس|الجزء الثاني)',txt):
        # lesson 1141 is a repost of lesson 2; use first occurrence to avoid a duplicate row.
        prefix=re.split(r'رابط الدرس|رابط',txt,maxsplit=1)[0].strip(' :👇🏼👇🏻')
        lesson_headers.append((prefix,m))
first_lesson={}
for label,m in lesson_headers:
    first_lesson.setdefault(label,m)

lesson_records=[]
lesson_summaries=[]
for idx,(lesson,m) in enumerate(first_lesson.items(),1):
    resolved=[]
    direct=[]
    unres=[]
    for a in m['links']:
        u=a['url'].strip(); target=parse_telegram_target(u)
        if target and target[0] in SELF_CHANNELS:
            tm=by_id.get(f'message{target[1]}')
            if tm:
                # A target can carry one or several attachments, otherwise save text / resource title as a record.
                names=[clean(x['name']) for x in tm['media'] if clean(x['name']) and clean(x['name']).lower()!='photo']
                if names:
                    for name in names:
                        key='media:'+name.lower(); ref=resource_by_key.get(key)
                        resolved.append((ref['resource_id'] if ref else '',name,tm['message_id'],tm['text']))
                else:
                    # link target is a direct linked/mentioned resource post; retain as a traceable pointer
                    text=clean(tm['text'])
                    resolved.append(('', text[:250] or f'local Telegram post {target[1]}',tm['message_id'],text))
            else:
                unres.append(u)
        elif target and target[0] in BOT_CHANNELS:
            continue
        else:
            # Direct external link; retain if it is not a generic course bot/channel handle.
            key='url:'+normalize_url(u); ref=resource_by_key.get(key)
            if ref:
                direct.append((ref['resource_id'],ref['candidate_title'],m['message_id'],ref['source_context']))
    combined=resolved+direct
    # exact duplicate items in a lesson are links repeated with several labels.
    seen=set(); ded=[]
    for item in combined:
        k=(item[0],item[1])
        if k not in seen:seen.add(k);ded.append(item)
    for item_no,(rid,title,source_mid,context) in enumerate(ded,1):
        lesson_records.append({
            'lesson_id':f'AYMAN-LESSON-{idx:02d}','original_lesson_label':lesson,'lesson_summary_message':m['message_id'],
            'item_number':item_no,'resource_id':rid,'candidate_title_or_target':title,'resolved_source_message':source_mid,
            'candidate_24week_placement':candidate_module_from_lesson(lesson),
            'review_risk':risk_from_title_and_lesson(title,lesson),
            'verification_status':'mentioned in original course export — not an approved course reading',
            'source_note':clean(context)[:800]
        })
    lesson_summaries.append({
        'lesson_id':f'AYMAN-LESSON-{idx:02d}','original_lesson_label':lesson,'summary_message':m['message_id'],
        'linked_items_resolved':len(ded),'unresolved_self_links':len(unres),'tentative_24week_placement':candidate_module_from_lesson(lesson),
        'summary_excerpt':clean(m['text'])[:1500]
    })

mfields=['resource_id','source_kind','resource_type','candidate_title','direct_url','source_message','source_messages','source_datetime','source_context','media_status','verification_status','rights_access_note','occurrences']
lfields=['lesson_id','original_lesson_label','lesson_summary_message','item_number','resource_id','candidate_title_or_target','resolved_source_message','candidate_24week_placement','review_risk','verification_status','source_note']
sfields=['lesson_id','original_lesson_label','summary_message','linked_items_resolved','unresolved_self_links','tentative_24week_placement','summary_excerpt']
for name,rows,fields in [
    ('01_full_resource_master_v0_1.csv',master,mfields),
    ('02_lesson_resource_map_v0_1.csv',lesson_records,lfields),
    ('03_lesson_catalogue_v0_1.csv',lesson_summaries,sfields),
]:
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

# High-value initial queue: resources whose earliest course placement is U1 or that are direct course media.
# Human-selected patterns avoid promoting legally/academically unverified material.
queue_terms=['ذواقة الشاي','شركات أنشئت لتبقى','القراءة السريعة','لماذا تفشل الأمم','الجماعات المتخيلة','الأصول الوسيطة','الدولتان','England in Egypt','إنجلترا في مصر','الشرق الأوسط الحديث','الفكر الاسلامي الحديث','استراتيجية الاستعمار','شروط النهضة','طبائع الاستبداد','مفهوم التاريخ','التاريخ الإسلامي','كيف يتعلم']
def title_for_match(value):
    return re.sub(r'[_\-]+',' ',value).lower()
queue=[]
for r in lesson_records:
    title_match=title_for_match(r['candidate_title_or_target'])
    if any(t.lower() in title_match for t in queue_terms): queue.append(r)
# retain unique by lesson/title, cap no items -- trace all qualifying.
qseen=set();q=[]
for r in queue:
    k=(r['original_lesson_label'],r['candidate_title_or_target'])
    if k not in qseen:qseen.add(k);q.append(r)
with (OUT/'04_editorial_review_queue_v0_1.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=lfields);w.writeheader();w.writerows(q)

# Human-readable report and orientation
ct=Counter(r['resource_type'] for r in master)
report=f'''# فهرسة تصدير: 1-تأسيس وعي المسلم المعاصر

## ما الذي فُحص؟

- المصدر: مجلد Google Drive الذي شاركه المستخدم بعنوان `ChatExport_2026-10-22 (1)`.
- الملف: `messages.html` (1,146,889 بايت).
- العنوان الظاهر داخل التصدير: **«1-تأسيس وعي المسلم المعاصر»**.
- الرسائل التي حملت محتوى: **{len(msgs)}**.
- خريطة الدروس المستخرجة من الفهارس المتأخرة: **{len(lesson_summaries)}** بطاقة درس أصلية، مع **{len(lesson_records)}** إحالة مورد/رابط تم حلّها حيث أمكن.
- سجل الموارد المستقلة بعد دمج تكرارات الاسم/الرابط واستبعاد روابط القناة إلى نفسها: **{len(master)}**.

| نوع المورد | العدد |
|---|---:|
'''
for k,v in sorted(ct.items()):report+=f'| `{k}` | {v} |\n'
report+='''
## ما تعنيه هذه الفهرسة

هذه القناة تقدّم **الإحالات والتكليفات والمستحبات المرافقة لدروس تأسيس وعي المسلم المعاصر**، بما فيها ملفات وكتب ومقاطع وروابط. هي مصدر غني لتتبع «ما ذُكر في سياق الدروس»، لكنها ليست تلقائياً قائمة القراءة المعتمدة في الدورة الجديدة ذات الـ24 أسبوعاً.

- حُفظت الروابط الداخلية للقناة بوصفها وصلات سياقية داخل خريطة الدروس، ولم تُحسب موارد مستقلة.
- حُفظت الملفات المسمّاة كبيانات وصفية فقط. لم ننزّل الكتب أو نعيد توزيعها.
- يبقى كل صف في حالة **مذكور في التصدير ويحتاج تحققاً ببليوغرافياً** حتى تثبيت المؤلف/العنوان/الطبعة/الناشر والإتاحة القانونية.
- المواد ذات الصلة بالفتن أو الجهاد أو الطوائف أو السياسة أو النزاعات المعاصرة تحمل تنبيه مراجعة متخصص؛ لا تصلح مادة عامة افتراضياً.

## الملفات

| الملف | وظيفته |
|---|---|
| `01_full_resource_master_v0_1.csv/.xlsx` | جميع أسماء المرفقات والروابط الخارجية المباشرة، مع رسالة الدليل وسياقها. |
| `02_lesson_resource_map_v0_1.csv/.xlsx` | وصل مورد/رابط بالدرس الأصلي الذي أحال إليه، مع موضع محتمل في الدورة الجديدة وتنبيه المخاطر. |
| `03_lesson_catalogue_v0_1.csv/.xlsx` | فهرس مختصر للدروس الأصلية وإحالاتها المحلولة. |
| `04_editorial_review_queue_v0_1.csv/.xlsx` | قائمة أولية أصغر لموارد تاريخية/منهجية تستحق التحقق أولاً؛ ليست مواداً مقررة. |

## بروتوكول الدمج مع مشروعنا

1. تبدأ عملية التحقق من عناصر `04_editorial_review_queue` ثم عناصر الوحدة 1 فقط.
2. يضاف إلى السجل المركزي فقط بعد: عنوان موثق، مؤلف/جهة، طبعة أو تاريخ، رابط قانوني، ناتج تعلم، وحدّ استعمال.
3. كل مورد حساس يُعرض معه مصدر بديل/قراءة مقابلة أو يُحال لمراجع اختصاص.
4. لا نستعمل اسم ملف PDF أو منشور Telegram بوصفه بيانات نشر نهائية.
'''
(OUT/'00_export_audit_and_integration.md').write_text(report,encoding='utf-8')

# XLSX format generator.
def write_xlsx(rows,fields,name,sheet):
    wb=Workbook();ws=wb.active;ws.title=sheet;ws.append(fields)
    for r in rows:ws.append([r.get(x,'') for x in fields])
    navy='13293D';thin=Side(style='thin',color='D6DEE3')
    for c in ws[1]:
        c.fill=PatternFill('solid',fgColor=navy);c.font=Font(name='Arial',color='FFFFFF',bold=True)
        c.alignment=Alignment(horizontal='right',vertical='center',wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font=Font(name='Arial',size=10);c.alignment=Alignment(horizontal='right',vertical='top',wrap_text=True);c.border=Border(bottom=thin)
    ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions;ws.row_dimensions[1].height=36
    for i,col in enumerate(ws.columns,1):
        ws.column_dimensions[get_column_letter(i)].width=min(max(max(len(str(c.value or '')) for c in col)*.68,12),52)
    if ws.max_row>1:
        tab=Table(displayName='DataTable',ref=f'A1:{get_column_letter(ws.max_column)}{ws.max_row}')
        tab.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showFirstColumn=False,showLastColumn=False,showRowStripes=True,showColumnStripes=False);ws.add_table(tab)
    wb.save(OUT/name)
write_xlsx(master,mfields,'01_full_resource_master_v0_1.xlsx','Resource Master')
write_xlsx(lesson_records,lfields,'02_lesson_resource_map_v0_1.xlsx','Lesson Resource Map')
write_xlsx(lesson_summaries,sfields,'03_lesson_catalogue_v0_1.xlsx','Lesson Catalogue')
write_xlsx(q,lfields,'04_editorial_review_queue_v0_1.xlsx','Editorial Queue')

# validated delivery package
files=list(OUT.iterdir())
zip_path=ROOT/'ayman_awareness_resource_index_v0_1.zip'
with ZipFile(zip_path,'w',ZIP_DEFLATED) as z:
    for p in files:
        if p.is_file():z.write(p,arcname=f'ayman_awareness_resource_index_v0_1/{p.name}')
    # raw trace is separated but useful for audit
    z.write(ROOT/'message_inventory.csv',arcname='ayman_awareness_resource_index_v0_1/audit_message_inventory.csv')
with ZipFile(zip_path) as z: assert z.testzip() is None
print(f'Master records: {len(master)}; lesson associations: {len(lesson_records)}; lessons: {len(lesson_summaries)}; review queue: {len(q)}')
print(zip_path)
