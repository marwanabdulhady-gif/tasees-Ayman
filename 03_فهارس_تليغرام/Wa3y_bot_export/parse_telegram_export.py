from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin, urlparse
import csv, re, html, json

src=Path('/home/user/wa3y_bot_export/messages.html')
out=Path('/home/user/wa3y_bot_export')
soup=BeautifulSoup(src.read_text(encoding='utf-8'), 'html.parser')
msgs=[]
for msg in soup.select('div.message.default'):
    mid=msg.get('id','')
    date_el=msg.select_one('.date.details')
    stamp=date_el.get('title','') if date_el else ''
    text_el=msg.select_one('.text')
    # Telegram export's .text excludes media filenames but contains content and links
    text=' '.join(text_el.stripped_strings) if text_el else ''
    links=[]
    if text_el:
        for a in text_el.find_all('a', href=True):
            href=a['href'].strip()
            if href:
                links.append({'url':href,'label':' '.join(a.stripped_strings)})
    # all media metadata in this message
    media=[]
    for m in msg.select('.media_file, .media_photo, .media_video, .media_audio, .media_voice_message'):
        title=m.select_one('.title.bold')
        desc=m.select_one('.description')
        status=m.select_one('.status.details')
        media.append({
            'kind':' '.join(m.get('class',[])),
            'name':' '.join(title.stripped_strings) if title else '',
            'description':' '.join(desc.stripped_strings) if desc else '',
            'status':' '.join(status.stripped_strings) if status else '',
        })
    hashtags=re.findall(r'(?<!\w)#([^\s#]+)', text)
    if text or media or links:
        msgs.append({'message_id':mid,'timestamp':stamp,'text':text,'links':links,'media':media,'hashtags':hashtags})

# all records by message (one row each)
with (out/'messages_parsed.json').open('w',encoding='utf-8') as f:
    json.dump(msgs,f,ensure_ascii=False,indent=2)
with (out/'message_inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['message_id','timestamp','text','media','links','hashtags'])
    w.writeheader()
    for x in msgs:
        w.writerow({'message_id':x['message_id'],'timestamp':x['timestamp'],'text':x['text'],'media':' | '.join(m['name'] for m in x['media']),'links':' | '.join(y['url'] for y in x['links']),'hashtags':' | '.join(x['hashtags'])})

# resource candidates: each hyperlink + each declared media file. Exclude internal hashtag empty hrefs and duplicate / empty
resources=[]
for x in msgs:
    for a in x['links']:
        u=a['url']
        if not u or u.startswith('#') or u.startswith('javascript:'):
            continue
        # showhashtag anchors omitted by blank href
        resources.append({'record_type':'link','title_or_label':a['label'],'url':u,'file_name':'','message_id':x['message_id'],'timestamp':x['timestamp'],'message_text':x['text'],'hashtags':' | '.join(x['hashtags'])})
    for m in x['media']:
        if m['name']:
            resources.append({'record_type':'attached_media','title_or_label':'','url':'','file_name':m['name'],'message_id':x['message_id'],'timestamp':x['timestamp'],'message_text':x['text'],'hashtags':' | '.join(x['hashtags'])})

# soft dedupe exact URL/media title, retain original occurrences + counts
keyed={}
for r in resources:
    key=(r['record_type'], r['url'].strip().lower() or re.sub(r'\s+',' ',r['file_name'].strip().lower()))
    if key not in keyed:
        keyed[key]={**r,'occurrences':1,'message_ids':[r['message_id']]}
    else:
        keyed[key]['occurrences']+=1
        keyed[key]['message_ids'].append(r['message_id'])

# heuristic category / suitability
BOOK_EXT=('.pdf','.epub','.mobi','.azw','.azw3','.djvu')
VID_HOSTS=('youtube.com','youtu.be','vimeo.com','drive.google.com')
def category(r):
    s=' '.join([r['title_or_label'],r['file_name'],r['url'],r['message_text']]).lower()
    if r['record_type']=='attached_media':
        if any(ext in s for ext in BOOK_EXT): return 'book_or_document_file'
        if any(w in s for w in ['mp3','m4a','audio','صوت']): return 'audio_file'
        if any(w in s for w in ['mp4','video','مرئي','فيديو']): return 'video_file'
        return 'attached_file_or_media'
    host=urlparse(r['url']).netloc.lower()
    if 't.me' in host: return 'telegram_post_or_channel'
    if 'youtube' in host or 'youtu.be' in host: return 'video'
    if 'drive.google' in host: return 'drive_resource'
    if any(ext in s for ext in BOOK_EXT): return 'book_or_document_link'
    if any(w in s for w in ['كتاب','book','قراءة','pdf','epub']): return 'book_or_document'
    if any(w in s for w in ['دورة','course','محاضرة','lecture']): return 'course_or_lecture'
    return 'web_resource'
def relevance(r):
    s=' '.join([r['title_or_label'],r['file_name'],r['message_text'],r['hashtags']])
    # triage: directly useful for full course, needing review, or likely outside immediate aims
    direct=['كيف أتعلم','تاريخ','وعي','منهج','تفكير','تأسيس','فلسف','علم النفس','لغة','سيرة','خلفاء','أموي','عباسي','قرآن']
    advanced=['عقيدة','حديث','تفسير','فقه','أصول','السياسة','اجتماع']
    if any(w in s for w in direct): return 'candidate_core_or_module_resource'
    if any(w in s for w in advanced): return 'candidate_enrichment_or_expert_review'
    return 'candidate_needs_editorial_review'

final=[]
for x in keyed.values():
    x['message_ids']=' | '.join(dict.fromkeys(x.pop('message_ids')))
    x['category']=category(x)
    x['initial_course_fit']=relevance(x)
    # simple copyright/access caution
    x['rights_note']='Do not redistribute attached/download links; verify lawful access and rights before assigning or sharing.' if x['record_type']=='attached_media' or x['category'].startswith('book') else 'Verify licence/access and bibliographic details before assignment.'
    final.append(x)
final.sort(key=lambda r:(r['initial_course_fit'],r['category'],r['title_or_label'] or r['file_name'] or r['url']))
fields=['record_type','category','initial_course_fit','title_or_label','file_name','url','message_id','message_ids','occurrences','timestamp','hashtags','message_text','rights_note']
with (out/'resource_candidates_raw_deduplicated.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(final)

# summaries
from collections import Counter
summary={'messages_with_content':len(msgs),'raw_resource_occurrences':len(resources),'deduplicated_resource_candidates':len(final),'record_types':Counter(r['record_type'] for r in final),'categories':Counter(r['category'] for r in final),'initial_fit':Counter(r['initial_course_fit'] for r in final),'file_mentions':sum(1 for r in final if r['record_type']=='attached_media'),'links':sum(1 for r in final if r['record_type']=='link')}
print(json.dumps(summary,ensure_ascii=False,indent=2))
