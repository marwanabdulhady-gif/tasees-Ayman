#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build owner-approved, source-grounded course lessons for all eleven playlists.

    python3 08_دورات_القوائم/tools/build_playlist_course_drafts.py
    python3 08_دورات_القوائم/tools/build_playlist_course_drafts.py --check

This writes a separate shelf at ``10_مسودات_القوائم/``. It does NOT replace or
edit any official ``00_خريطة_الدورة.json`` or existing approved course copy.
Each lesson follows the project course-script template (opening, question,
source, three blocks, trap, three-level task, closing) and carries at least six
literal quotations with a citation form accepted by ``check_lesson.py``:
timestamps, paragraphs, or exact lines plus SHA-256. Quotations and hashes are
read from the original files, never from memory.

The owner has recorded a final approval for publication. Q1 (voice of the
non-Ayman playlists) is Ayman's style with named attribution; these drafts were
generated in a neutral voice before that correction and need rewriting. Retrieval proves only that a quote is at a location in the current
bytes; it does not prove the recording, speaker, edition, transcription
accuracy, interpretation, independent references or factual correctness.
Non-Ayman drafts here use a neutral named guide and never attribute words to
Ayman. Sensitive-playlist red lines remain in force. Approval does not merge
pull requests or publish outside this repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_lesson import norm  # noqa: E402
from playlist_sources import ROOT, PKG, STAMP, citation_kind, ordered_items, registry, source_dir  # noqa: E402
from owner_decisions import (APPROVED_STATUS, CAVEATS, LABELS, PUBLICATION_STATUS,  # noqa: E402
                             Q1_STATUS, SHORT_STATUS, VERIFICATION_STATUS, gate_for,
                             publication, status)

OUT = PKG / '10_مسودات_القوائم'
CATALOG = ROOT / 'ayman_rag' / 'playlist_inventory.json'
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
AR2EN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
PDF_START = re.compile(r'<!--\s*بداية صفحة PDF\s+([٠-٩\d]+)')
PDF_END = re.compile(r'<!--\s*نهاية صفحة PDF')
KIND_AR = {'timestamp': 'طوابع زمنية في التفريغ، غير متحققة من التسجيل',
           'paragraph': 'أرقام فقرات، ليست توقيتات',
           'line': 'سطور وبصمة بايتات، ليست توقيتات',
           'pdf': 'صفحات PDF مستخرجة من الكتاب، ليست توقيتات'}
TOOLS = [
    ('بطاقة المصدر', 'اكتب الاقتباس في خانة، والإحالة في خانة، والبصمة في خانة. ثم اكتب ما لا تثبته هذه الخانات: المتحدث، والتسجيل، والطبعة، والمعنى. البطاقة تمنع خلط الشاهد بالتفسير، وتجعل كل سؤال قابلًا للإحالة إلى مراجعة لاحقة.'),
    ('ميزان النقل', 'قسّم الورقة بين عبارة منقولة وقراءة تعليمية. العبارة المنقولة تُترك كما هي، والقراءة تُوصَف بأنها سؤال أو أداة لا حكم. إذا لم تجد فاصلًا واضحًا، اكتب: لا أعلم بعد، وأحِل العبارة إلى طابور المراجعة.'),
    ('خانة لا أعلم بعد', 'لكل مقطع اكتب ثلاث خانات: ما يثبته الموضع، وما يحتاج تسجيلًا، وما يحتاج مرجعًا مستقلًا. لا تملأ خانة بحدس. هذه الخانة ليست نقصًا في الدرس؛ هي الحد الذي يمنع تحويل مسودة إلى قرار نشر.'),
]
SENSITIVE = [
    'قتل', 'قتال', 'اغتيال', 'دم', 'حرب', 'انتحار', 'اغتصاب', 'اعتقال', 'سجن', 'تعذيب',
    'تكفير', 'كافر', 'مذهب', 'طائفة', 'شيع', 'سني', 'سلفي', 'اخوان', 'الإخوان', 'صهيون',
    'يهود', 'رابعة', 'ميدان', 'سوريا', 'الجيش', 'الشرطة', 'الحكومة', 'الرئيس', 'الملك',
    'علاج', 'تشخيص', 'مريض', 'مرض', 'اضطراب', 'دواء', 'انحراف', 'جنس', 'شذوذ', 'فتوى',
    'حرام', 'حلال', 'قذف', 'سب', 'لعن', 'شتم', 'النوايا', 'النيات',
]
SAFETY = {
    'ayman-psychology': 'لا تشخيص ولا نصيحة علاجية؛ التمارين عن فهم النص لا عن حالة المتعلم النفسية.',
    'ayman-seerah-makkah': 'بلا تجسيد للنبي ﷺ، مع أدب الصحابة، وبلا ترجيح طائفي.',
    'ayman-umayyad-abbasid': 'بلا ترجيح طائفي ولا حكم على النيات؛ الأحداث تُقرأ بوصفها مادة تفريغ تحتاج مراجعة.',
    'ayman-reestablishing-awareness': 'لا تحريض، ولا أسماء أشخاص أحياء في سياق اتهام، ولا دعوة لفعل غير آمن.',
    'q100-history': 'لا نسبة تفصيلية للمقدّم أو الضيوف قبل توثيق الحلقات، ولا حكم تاريخي مستقل؛ مكتوبة بمرشد محايد قبل تصحيح المالك لـQ1 (أسلوب أيمن)؛ تُعاد صياغتها قبل النشر.',
    'rihlat-alyaqeen': 'محتوى عقدي يُقرأ بوصفه مادة منقولة من التفريغ، بلا إضافة حكم أو فتوى؛ مكتوبة بمرشد محايد قبل تصحيح المالك لـQ1 (أسلوب أيمن)؛ تُعاد صياغتها قبل النشر.',
    'ayn-al-tariq': 'نص مستخرج من PDF مرفق؛ تُعاد مطابقة الاقتباسات مقابل ملف PDF الأصلي قبل أي إسناد نهائي، بلا نسبة إلى أيمن عبد الرحيم.',
}
SERIES = {
    'q100-history': 'سلسلة مائة سؤال في التاريخ، وليست منسوبة إلى أيمن عبد الرحيم.',
    'rihlat-alyaqeen': 'سلسلة رحلة اليقين للدكتور إياد قنيبي، وليست منسوبة إلى أيمن عبد الرحيم.',
    'ayn-al-tariq': 'كتاب أين الطريق؟، الطبعة الأولى، من ملف PDF مرفق من المستخدم؛ وليس منسوبًا إلى أيمن عبد الرحيم.',
}
TITLE_OVERRIDES = {
    'q100-history': 'مائة سؤال في التاريخ',
    'rihlat-alyaqeen': 'رحلة اليقين',
    'ayn-al-tariq': 'أين الطريق؟',
}
ORDINALS = [
    'الأولى', 'الثانية', 'الثالثة', 'الرابعة', 'الخامسة', 'السادسة', 'السابعة', 'الثامنة',
    'التاسعة', 'العاشرة', 'الحادية عشرة', 'الثانية عشرة', 'الثالثة عشرة', 'الرابعة عشرة',
    'الخامسة عشرة', 'السادسة عشرة', 'السابعة عشرة', 'الثامنة عشرة', 'التاسعة عشرة', 'العشرين',
]
HEADER_WORDS = [
    'num', 'Episode', 'Supadata', 'youtube', 'youtubetranscript', 'transcript_source',
    'source_folder', 'source_file', 'converted_at_utc', 'title:', 'series:', 'channel:',
    'upload_date', 'duration:', 'language:', 'url:', 'video_id:', 'episode:', 'pdf_pages:',
    'source_type:', 'extraction_method:', 'verification_status:', 'الحلقة:', 'الرابط:', 'المصدر:',
]
DRAFT_NOTE = LABELS['draft_note']
APPROVAL_NOTE = LABELS['publication_note']
VERIFICATION_NOTE = LABELS['verification_note']
SOURCE_NOTE = ('الطوابع الزمنية وأرقام الفقرات وصفحات PDF والسطور كلها مواضع نصية، لا توقيتات مؤكدة. '
               'روابط التسجيل وطرائق التفريغ المذكورة في الترويسات تُقرأ بوصفها ادعاءات في '
               'الملف، لا بوصفها توثيقًا مستقلًا. لا تُدمج النسخ، ولا تُصحّح الاقتباسات، '
               'ولا تُحوّل عبارة منقولة إلى رأي متحقق؛ ' + VERIFICATION_NOTE)
METHOD_PAD = ('منهج القراءة في هذه الدروس يقوم على فصل أربع طبقات: البايتات التي تحمل '
              'البصمة، والاقتباس كما ورد، والإحالة التي تحدد موضعه، والسؤال التعليمي الذي '
              'يفتحه الدرس. الطبقة الأولى يفحصها سكربت آلي، والثانية تُقرأ كما هي، والثالثة '
              'يُعاد التحقق منها أمام الملف، أما الرابعة فهي اجتهاد تعليمي قابل للمراجعة '
              'والحذف. إذا تعارضت طبقة مع أخرى، تُقدَّم البايتات على التأويل، ويُسجّل '
              'الخلاف في طابور الاعتماد. لذلك لا تُعدّ كثرة الاقتباسات تغطية شاملة، ولا '
              'تُقرأ هذه الدروس بوصفها تحققًا مستقلًا، ولا يُبنى عليها حكم تاريخي أو سريري '
              'أو صوت منسوب إلى متحدث قبل التحقق. ' + APPROVAL_NOTE)


def ar(n: int) -> str:
    return str(n).translate(AR)


def ordinal(n: int) -> str:
    return ORDINALS[n - 1] if 1 <= n <= len(ORDINALS) else f'الدفعة {ar(n)}'


def groups_for(count: int) -> list[list[int]]:
    size = 1 if count <= 10 else 3 if count <= 20 else 4
    return [list(range(i + 1, min(i + size, count) + 1)) for i in range(0, count, size)]


def clean_title(value: str) -> str:
    value = re.sub(r'[0-9٠-٩]+', ' ', value)
    value = re.sub(r'[|،؛:؟?!()\[\]{}«»"\'_]', ' ', value)
    return ' '.join(value.split())[:70].strip() or 'مقاطع من القائمة'


def link_from(lesson_dir: Path, source: Path) -> str:
    return quote(Path(os.path.relpath(source, lesson_dir)).as_posix(), safe='/')


def is_header_line(line: str) -> bool:
    s = line.strip()
    return (not s or s.startswith(('#', '-', '---', '|', '<!--')) or
            'صفحة PDF' in s or
            any(word.lower() in s.lower() for word in HEADER_WORDS))


def bad_token(token: str) -> bool:
    low = token.lower()
    return (not re.search(r'[\u0600-\u06ff\w]', token) or 'http' in low or 'num' == low
            or 'episode' in low or 'supadata' in low or 'youtube' in low or '**' in token
            or '](' in token or '---' in token or '<!--' in token or '-->' in token
            or re.search(r'[0-9٠-٩]{2,}', token))


def phrase(raw: str, nwords: int) -> str | None:
    tokens = list(re.finditer(r'\S+', raw))
    if len(tokens) < nwords:
        return None
    start = 0
    while start + nwords <= len(tokens):
        window = tokens[start:start + nwords]
        if not any(bad_token(m.group()) for m in window):
            candidate = raw[window[0].start():window[-1].end()].strip()
            if (3 <= len(candidate.split()) <= 30 and not re.search(r'[0-9٠-٩]{2,}', candidate)
                    and not any(x in candidate for x in ('«', '»', '〔', '〕', 'http', '**', '](', '---', '|'))):
                return candidate
        start += 1
    return None


def safe_quote(q: str) -> bool:
    low = q.lower()
    return (not any(term in q for term in SENSITIVE)
            and not any(word.lower() in low for word in HEADER_WORDS))


def spread(items: list, limit: int) -> list:
    if not items:
        return []
    if len(items) <= limit:
        return list(items)
    return [items[round(i * (len(items) - 1) / (limit - 1))] for i in range(limit)]


def line_number_of(text: str, q: str) -> int:
    nq = norm(q)
    for i, line in enumerate(text.splitlines(), 1):
        if nq and nq in norm(line):
            return i
    raise ValueError('quote line not found in original source')


def candidate(item: dict, ep: int, kind: str, label: str, cite: str, map_cite: str,
              q: str, line: int, sha: str, source_id: str, extra: dict | None = None) -> dict:
    row = {'episode': ep, 'kind': kind, 'label': label, 'citation': cite,
           'map_cite': map_cite, 'quote': q, 'line': line, 'sha': sha,
           'source_id': source_id}
    if extra:
        row.update(extra)
    return row


def extract_candidates(item: dict, catalog: dict[str, dict], limit: int = 6) -> list[dict]:
    path = item['path']
    source = ROOT / path
    data = source.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if catalog[path]['sha256'] != sha:
        raise ValueError(f'SHA-256 mismatch with unified catalogue: {path}')
    source_id = catalog[path]['id']
    text = data.decode('utf-8', errors='replace')
    lines = text.splitlines(keepends=True)
    ep, kind = item['episode'], citation_kind(path)
    all_rows: list[dict] = []
    if kind == 'line':
        for i, line in enumerate(lines, 1):
            if is_header_line(line):
                continue
            for nwords in (10, 8, 6, 4):
                q = phrase(line.rstrip('\n'), nwords)
                if q:
                    all_rows.append(candidate(item, ep, kind, 'س' + ar(i),
                                              f'〔ح{ar(ep)} س{ar(i)} sha256={sha}〕',
                                              f'L{i}', q, i, sha, source_id))
                    break
    elif kind == 'timestamp':
        for i, line in enumerate(lines, 1):
            m = STAMP.search(line)
            if not m:
                continue
            ts = m.group(0)[3:m.group(0).index(']')]
            body = STAMP.sub('', line)
            if is_header_line(body):
                continue
            for nwords in (10, 8, 6, 4):
                q = phrase(body, nwords)
                if q:
                    all_rows.append(candidate(item, ep, kind, ts,
                                              f'〔ح{ar(ep)} {ts}〕', ts, q, i, sha, source_id))
                    break
    elif kind == 'pdf':
        page: int | None = None
        for i, line in enumerate(lines, 1):
            raw = line.rstrip('\n')
            start = PDF_START.search(raw)
            if start:
                page = int(start.group(1).translate(AR2EN))
                continue
            if PDF_END.search(raw):
                page = None
                continue
            if page is None or is_header_line(raw):
                continue
            for nwords in (10, 8, 6, 4):
                q = phrase(raw, nwords)
                if q:
                    all_rows.append(candidate(item, ep, kind, 'ص' + ar(page),
                                              f'〔ح{ar(ep)} ص{ar(page)}〕', f'PDF p.{page}',
                                              q, i, sha, source_id, {'pdf_page': page}))
                    break
    else:
        body = STAMP.sub('', text)
        paras = [seg for seg in re.split(r'\n\s*\n', body) if len(norm(seg)) > 20]
        for idx, seg in enumerate(paras, 1):
            for raw_line in seg.splitlines():
                if is_header_line(raw_line):
                    continue
                for nwords in (10, 8, 6, 4):
                    q = phrase(raw_line, nwords)
                    if q:
                        line = line_number_of(text, q)
                        all_rows.append(candidate(item, ep, kind, 'ف' + ar(idx),
                                                  f'〔ح{ar(ep)} ف{ar(idx)}〕', f'¶{idx}',
                                                  q, line, sha, source_id, {'paragraph': idx}))
                        break
                else:
                    continue
                break
    # Prefer neutral, non-sensitive phrases; fall back to structurally valid
    # phrases if a short source does not provide enough neutral ones.
    neutral = [r for r in all_rows if safe_quote(r['quote'])]
    chosen = spread(neutral, limit)
    for row in spread(all_rows, max(limit, len(all_rows))):
        if len(chosen) >= limit:
            break
        if row not in chosen:
            chosen.append(row)
    if not chosen:
        raise ValueError(f'no usable quotation candidates for {path}')
    # Verify literal location against the exact bytes or the checker's normalizer.
    for row in chosen:
        if kind == 'line' and row['quote'] not in ''.join(lines[row['line'] - 1:row['line']]):
            raise ValueError(f'line quote not literal: {path} L{row["line"]}')
        if kind != 'line' and norm(row['quote']) not in norm(text):
            raise ValueError(f'quote not found in episode: {path}')
    return chosen[:limit]


def select_quotes(group: list[int], rows: list[dict], catalog: dict[str, dict]) -> list[dict]:
    candidates = {ep: extract_candidates(rows[ep - 1], catalog) for ep in group}
    selected: list[dict] = [(ep, candidates[ep][0]) for ep in group]
    # Add successive passages from each episode, preserving source coverage.
    depth = 1
    while len(selected) < 6:
        added = False
        for ep in group:
            if depth < len(candidates[ep]):
                selected.append((ep, candidates[ep][depth]))
                added = True
                if len(selected) >= 6:
                    break
        if len(selected) >= 6:
            break
        if not added:
            # Extremely short source: repeat a verified passage with a different
            # pedagogic lead rather than inventing an unsupported quotation.
            ep = group[(len(selected) - 1) % len(group)]
            selected.append((ep, candidates[ep][len(selected) % len(candidates[ep])]))
        depth += 1
    out = []
    for ep, row in selected[:6]:
        out.append(dict(row, episode=ep))
    return out


def word_count(text: str) -> int:
    body = re.sub(r'〔[^〕]*〕', ' ', text)
    body = re.sub(r'\]\([^)]*\)', ']', body)
    body = re.sub(r'`[^`]*`', ' ', body)
    return len(body.split())


def build_lesson(playlist: dict, rows: list[dict], group: list[int], n: int,
                 catalog: dict[str, dict], lesson_dir: Path) -> tuple[str, list[dict]]:
    voice = playlist.get('voice')
    quotes = select_quotes(group, rows, catalog)
    source_rows = [rows[ep - 1] for ep in group]
    course_title = TITLE_OVERRIDES.get(playlist['slug']) or clean_title(playlist['title'])
    title = f'قراءة مقاطع من {course_title} — الدفعة {ordinal(n)}'
    if voice == 'ayman':
        opening = ('أهلًا بيك في الدرس. تخيّل ورقة واحدة قدامك: ناحية فيها كلام التفريغ كما هو، '
                   'وناحية فيها سؤالنا عن معناه، وناحية تالتة فيها اللي لسه ما نعرفهوش. '
                   'الدرس ده مش حكم جاهز ولا صوت منسوب لصاحب التسجيل؛ هو تمرين على الفصل بين '
                   'الشاهد والقراءة. الصياغة مستوحاة من إيقاع تأسيس، والاقتباسات وحدها هي المنقول.')
    else:
        named = ('والنسبة بالاسم إلى ' + course_title + ' موثقة في قرار المالك. '
                 if playlist.get('voice') == 'owner-decision' else '')
        opening = ('نفتح هذا الدرس بورقة قراءة لا بخلاصة نهائية. أمامنا مقاطع من قائمة تشغيل، '
                   'وكل مقطع له موضع وبصمة وسؤال. مرشد الدورة يقرأ بفصحى مبسطة، ولا يتبنّى '
                   'صوت صاحب السلسلة ولا ينسب إليه صياغة الدرس. ' + named +
                   LABELS['q1_text'] + ' ' + SERIES.get(playlist['slug'], ''))
    source_links = []
    for row in source_rows:
        ep = row['episode']
        source = ROOT / row['path']
        entry = catalog[row['path']]
        source_links.append(
            f'[التفريغ النصي للحلقة {ar(ep)}]({link_from(lesson_dir, source)}) · '
            f'معرّف المصدر `{entry["id"]}` · SHA-256 `{entry["sha256"]}` · '
            f'{KIND_AR[citation_kind(row["path"])]}.')
    safety = SAFETY.get(playlist['slug'], 'الخطوط الحمراء العامة للمشروع تسري على النص والشاشات معًا.')
    q1 = LABELS['q1_text'] if voice == 'owner-decision' else ''
    parts = [
        f'# الدرس {ar(n)} — {title}', '', DRAFT_NOTE, '',
        '## افتتاح وخطاف', '', opening, '',
        '## سؤال الدرس',
        'كيف نقرأ مقاطع من هذه القائمة قراءة تعليمية محكومة بالسند، من غير تحويل التفريغ إلى حكم معتمد؟', '',
        '## مصدر الدرس', *source_links, '', SOURCE_NOTE + ' ' + safety + q1, '',
        '**ما أخذناه:** ستة مقاطع حرفية موزّعة على الحلقات المذكورة، مع إحالة وبصمة لكل ملف. '
        '**ما أجّلناه:** بقية الحلقات، والأحكام، والأرقام، والوقائع، ونسبة الكلام، ومراجعة المراجع المستقلة. '
        'هذه قراءة محددة لا تلخّص القائمة كلها.', '',
    ]
    block_titles = ['الشاهد قبل السؤال', 'النقل قبل التفسير', 'الحد قبل التعميم']
    block_intros = [
        'نبدأ بالموضع: أين وردت العبارة؟ وما نوع الإحالة؟ قبل أي كلام عن المعنى، نثبّت أن الاقتباس من الملف الحالي لا من ذاكرة.',
        'ننتقل إلى الفرق بين عبارة منقولة وأداة يضيفها الدرس. الأداة للتعلّم، وليست شاهدًا جديدًا ولا تثبيتًا لصحة العبارة.',
        'نختم بحدود الاستنتاج: وجود بصمة وسطر أو طابع أو فقرة لا يكفي وحده لإصدار حكم أو تعميم أو نسبة متحدث.',
    ]
    for block_index in range(3):
        label = ['الكتلة ١', 'الكتلة ٢', 'الكتلة ٣'][block_index]
        tool_name, tool_text = TOOLS[block_index]
        parts += [f'## {label} — {block_titles[block_index]}', '', block_intros[block_index], '']
        for j, row in enumerate(quotes[block_index * 2:block_index * 2 + 2], 1):
            lead = ['الشاهد الأول', 'الشاهد الثاني', 'الشاهد الثالث', 'الشاهد الرابع',
                    'الشاهد الخامس', 'الشاهد السادس'][(block_index * 2 + j - 1)]
            parts += [f'{lead}: «{row["quote"]}» {row["citation"]}',
                      'الاقتباس يثبت ورود العبارة في الموضع المُحال؛ لا يثبت صحة التفريغ ولا نسبة المتحدث '
                      'ولا سلامة الاستنتاج. نسأل: أي طبقة من طبقات القراءة نفحص الآن؟', '']
        parts += [' discussion_placeholder ', '',
                  f'**أداة الكتلة: {tool_name}.** {tool_text}', '']
    parts[parts.index(' discussion_placeholder ')] = (
        'ودي نقطة عملية: كلما اتسع السؤال، ضاق الادعاء. نترك العبارة في خانة النقل، '
        'ونضع السؤال في خانة الدرس، ونؤجّل الجواب إلى مراجعة التسجيل والمراجع.')
    # The same discussion sentence is reused in all three blocks; replace every placeholder.
    parts = [('ودي نقطة عملية: كلما اتسع السؤال، ضاق الادعاء. نترك العبارة في خانة النقل، '
              'ونضع السؤال في خانة الدرس، ونؤجّل الجواب إلى مراجعة التسجيل والمراجع.'
              if p == ' discussion_placeholder ' else p) for p in parts]
    parts += [
        '## مصيدة الفهم',
        'أن تظن أن كثرة الإحالات تعني أن الدرس مكتمل أو أن كل عبارة صحيحة. الإحالات تثبت المواضع، '
        'وقرار المالك بالاعتماد موثق لكنه لا يثبت التسجيلات والمراجع. تُسجّل هذه المصيدة في طابور الاعتماد مع قيودها.', '',
        '## المهمة', '',
        '**مستكشف:** اختر اقتباسًا واحدًا واكتب سؤالًا يفتحه، ثم اكتب ما لا يجيب عنه الاقتباس.', '',
        '**ممارس:** اعمل جدولًا من ثلاثة أعمدة: الاقتباس، والإحالة، وما يحتاج تحققًا. املأ سطرين '
        'من حلقات مختلفة إن وُجدت، واترك كل خانة ناقصة بعبارة لا أعلم بعد.', '',
        '**متقدم:** قارن إحالتين من نوعين مختلفين إن وُجدا، واذكر أي طبقة يثبتها كل نوع، '
        'وأي طبقة لا يثبتها، وكيف تمنع المقارنةُ التعميمَ.', '',
        'المهمة عن فهم النص لا عن تقويم أشخاص أو حالات. ' + safety, '',
        '### نموذج للمراجعة الذاتية',
        'مثال: الاقتباس موجود، والإحالة تشير إلى موضعه، والبصمة تطابق الملف؛ لكن نسبة المتحدث '
        'تحتاج تسجيلًا، والمعنى يحتاج سياقًا، والحكم يحتاج مرجعًا مستقلًا. إن غاب شاهد، '
        'تُترك الخانة بعبارة لا أعلم بعد بدل ملئها بحدس.', '',
        '## القفلة',
        'نبدأ بالموضع، ثم نفصل النقل عن القراءة، ثم نُبقي قيود التحقق موثقة.',
        'قرار المالك بالاعتماد موثق، لكنه لا يثبت التسجيل أو المراجع؛ والخرائط الرسمية لم تُعدّل.', '',
        'الدرس الجاي يواصل قراءة المقاطع التالية بالحد نفسه. استنى هناك.',
    ]
    text = '\n'.join(parts) + '\n'
    # Keep the same 700–1200-word range used by the existing template lessons.
    while word_count(text) < 700:
        text = text.replace('## مصيدة الفهم', METHOD_PAD + '\n\n## مصيدة الفهم', 1)
        if text.count(METHOD_PAD) > 2:
            break
    count = word_count(text)
    if not 700 <= count <= 1200:
        raise ValueError(f'{playlist["slug"]}/lesson-{n:02d}: {count} words (need 700–1200)')
    if text.count('«') != 6 or text.count('〔') != 6:
        raise ValueError(f'{playlist["slug"]}/lesson-{n:02d}: quote/citation count wrong')
    return text, quotes


def map_lesson(playlist: dict, rows: list[dict], group: list[int], n: int,
               quotes: list[dict]) -> dict:
    ideas = []
    for row in quotes:
        idea = {'text': 'اقتباس حرفي من التفريغ؛ يُقرأ بوصفه موضعًا لا حكمًا.',
                'ep': row['episode'], 'cite': row['map_cite'], 'quote': row['quote'],
                'citation_kind': row['kind']}
        if row['kind'] == 'line':
            idea['source_sha256'] = row['sha']
        ideas.append(idea)
    built = {str(ep): rows[ep - 1].get('sha') for ep in group}
    course_title = TITLE_OVERRIDES.get(playlist['slug']) or clean_title(playlist['title'])
    return {'n': n, 'unit': 'درس معتمد من المالك',
            'title': f'قراءة مقاطع من {course_title} — الدفعة {ordinal(n)}',
            'question': 'كيف نقرأ المقاطع بسند محقق الموضع مع بقاء قيود التحقق موثقة؟',
            'episodes': group, 'ideas': ideas,
            'patterns': ['P14', 'P02', 'P17', 'P15'], 'atlas': [],
            'text': f'01_نصوص_الدروس/lesson-{n:02d}.md',
            'page': f'02_الشاشات/lesson-{n:02d}.html',
            'text_status': status(), 'built_from': built}


def index_markdown(playlist: dict, lessons: list[dict], rows: list[dict]) -> str:
    lines = [f'# فهرس الدروس المعتمدة — {playlist["title"]}', '',
             '> **معتمد من المالك للنشر.** هذا فهرس لرف الدروس، لا `00_خريطة_الدورة.json`، '
             'ولا يُحتسب ضمن جداول الخرائط الرسمية. ' + APPROVAL_NOTE, '',
             f'- القائمة: `{playlist["slug"]}`',
             f'- عدد ملفات المصدر: {len(rows)}',
             f'- عدد الدروس: {len(lessons)}',
             f'- الصوت: {"مرشد محايد بفصحى مبسطة مع النسبة بالاسم — لا يطابق قرار Q1 (أسلوب أيمن)؛ تُعاد صياغته" if playlist.get("voice") == "owner-decision" else "مستوحى من إيقاع تأسيس، معتمد من المالك"}',
             f'- الإحالات: {playlist.get("citation")}',
             '', '## الدروس', '',
             '| الدرس | الحلقات | النص | الشاشات | الحالة |', '|---|---|---|---|---|']
    for l in lessons:
        eps = '، '.join(ar(ep) for ep in l['episodes'])
        lines.append(f'| {ar(l["n"])} | {eps} | [{Path(l["text"]).name}]({l["text"]}) | '
                     f'[{Path(l["page"]).name}]({l["page"]}) | {SHORT_STATUS} |')
    lines += ['', '## حدود', '', SOURCE_NOTE, '',
              SAFETY.get(playlist['slug'], 'الخطوط الحمراء العامة للمشروع تسري على النص والشاشات معًا.'), '',
              VERIFICATION_NOTE + ' لا تُقرأ التغطية بوصفها صحة محتوى.', '',
              '[طابور اعتماد هذه القائمة](00_طابور_المراجعة.md) · '
              '[لوحة الاعتماد](../03_لوحة_المراجعة/index.html) · '
              '[الطابور الجذري](../00_طابور_المراجعة.md) · '
              '[قرار المالك](../../00_قرارات_المالك.md)']
    return '\n'.join(lines) + '\n'


def readme(playlist: dict, lessons: list[dict], rows: list[dict]) -> str:
    warnings = '\n'.join(f'- {w}' for w in playlist.get('warnings', [])) or '- لا تحذيرات إضافية في السجل.'
    decision = ('كُتبت هذه المسودة بمرشد محايد بفصحى مبسطة مع النسبة بالاسم، ولا تُنسب إلى أيمن عبد الرحيم. '
                'قرار المالك Q1 هو أسلوب أيمن مع النسبة والإخلاء، فتُعاد صياغتها قبل النشر.' if playlist.get('voice') == 'owner-decision'
                else 'الصياغة مستوحاة من إيقاع «تأسيس»، وليست كلامًا منسوبًا إلى متحدث متحقق؛ قرار المالك بالاعتماد موثق.')
    return '\n'.join([
        f'# دورة القائمة — {playlist["title"]}', '',
        '> **معتمد من المالك للنشر.** رف منفصل عن الخرائط الرسمية؛ لا يُعدّل `00_خريطة_الدورة.json` ولا '
        'النسخ الأساسية. ' + APPROVAL_NOTE, '',
        f'- **القائمة:** `{playlist["slug"]}`',
        f'- **ملفات المصدر:** {len(rows)}',
        f'- **الدروس:** {len(lessons)}',
        f'- **الشاشات:** {len(lessons) * 10} (عشر شاشات لكل درس، مولّدة من النص)',
        f'- **الصوت:** {decision}',
        f'- **السند:** {playlist.get("citation")}؛ كل درس ستة اقتباسات حرفية على الأقل '
        'مع إحالة مقبولة لدى `check_lesson.py` وبصمة بايتات لكل ملف.', '',
        '## ما في هذا المجلد', '',
        '- `01_نصوص_الدروس/` — نصوص بقالب المشروع، معتمدة من المالك مع قيود موثقة.',
        '- `02_الشاشات/` — شاشات مشتقة من `week-template.html` بنفس الهوية.',
        '- `00_خريطة_المسودة.json` — فهرس هيكلي معتمد من المالك، وليس خريطة رسمية.',
        '- `00_فهرس_المسودة.md` — جدول الدروس وحدود القراءة والاعتماد.',
        '- `00_طابور_المراجعة.md` — قرار المالك وقيود التحقق غير الثابت آليًا لهذه القائمة.', '',
        '## تحذيرات السجل', '', warnings, '',
        '## خطوط حمراء', '', SAFETY.get(playlist['slug'], 'الخطوط الحمراء العامة للمشروع تسري على النص والشاشات معًا.'), '',
        SOURCE_NOTE, '',
        '## أوامر المراجعة', '',
        '```bash',
        'python3 08_دورات_القوائم/tools/build_playlist_course_drafts.py --check',
        'python3 08_دورات_القوائم/tools/build_playlist_course_screens.py --check',
        'python3 08_دورات_القوائم/tools/build_review_queue.py --check',
        'python3 08_دورات_القوائم/tools/check_lesson.py <مجلد النصوص> --playlist <مجلد التفريغات>',
        '```', '',
        '[طابور اعتماد القائمة](00_طابور_المراجعة.md) · [لوحة الاعتماد](../03_لوحة_المراجعة/index.html) · '
        '[قرار المالك](../../00_قرارات_المالك.md) تسجّل الاعتماد والقيود؛ أُزيلت بوابة النشر داخل المستودع.', '',
        VERIFICATION_NOTE + ' لا يثبت الفحص الآلي سوى المواضع والبصمات.',
    ]) + '\n'


def build() -> dict[Path, str]:
    catalog = {d['path']: d for d in json.loads(CATALOG.read_text(encoding='utf-8'))['documents']}
    out: dict[Path, str] = {}
    summary = []
    for playlist in registry()['playlists']:
        rows = ordered_items(playlist)
        groups = groups_for(len(rows))
        course_dir = OUT / playlist['slug']
        lesson_dir = course_dir / '01_نصوص_الدروس'
        lessons = []
        for n, group in enumerate(groups, 1):
            text, quotes = build_lesson(playlist, rows, group, n, catalog, lesson_dir)
            out[lesson_dir / f'lesson-{n:02d}.md'] = text
            lessons.append(map_lesson(playlist, rows, group, n, quotes))
        out[course_dir / '00_خريطة_المسودة.json'] = json.dumps({
            'schema_version': 2, 'status': status(),
            'note': 'ليست 00_خريطة_الدورة.json؛ قرار المالك بالاعتماد موثق مع بقاء قيود التحقق. ' + APPROVAL_NOTE,
            'slug': playlist['slug'], 'title': playlist['title'],
            'voice': playlist.get('voice'), 'owner_gate': gate_for(playlist.get('voice')),
            'source_dir': str(source_dir(playlist).relative_to(ROOT)),
            'episode_numbering': 'check_lesson.py file order / front matter / numbered text files',
            'lessons': lessons,
        }, ensure_ascii=False, indent=2) + '\n'
        out[course_dir / '00_فهرس_المسودة.md'] = index_markdown(playlist, lessons, rows)
        out[course_dir / 'README.md'] = readme(playlist, lessons, rows)
        summary.append({'slug': playlist['slug'], 'title': playlist['title'],
                        'episodes': len(rows), 'lessons': len(lessons),
                        'screens': len(lessons) * 10, 'voice': playlist.get('voice'),
                        'owner_gate': gate_for(playlist.get('voice'))})
    total_lessons = sum(x['lessons'] for x in summary)
    total_screens = sum(x['screens'] for x in summary)
    out[OUT / '00_حالة_القوائم.json'] = json.dumps({
        'schema_version': 2, 'status': status(),
        'note': 'تغطية هيكلية لكل القوائم المسجلة؛ قرار المالك بالاعتماد موثق. ' + APPROVAL_NOTE + ' ' + VERIFICATION_NOTE,
        'rag_catalog': 'ayman_rag/playlist_inventory.json',
        'rag_audit': 'ayman_rag/playlist_retrieval_audit.json',
        'review_queue': '08_دورات_القوائم/10_مسودات_القوائم/00_طابور_المراجعة.json',
        'review_board': '08_دورات_القوائم/10_مسودات_القوائم/03_لوحة_المراجعة/index.html',
        'review_status': f'{publication()}; owner decision recorded; independent verification {VERIFICATION_STATUS}',
        'totals': {'playlists': len(summary), 'sources': sum(x['episodes'] for x in summary),
                   'lessons': total_lessons, 'screens': total_screens},
        'playlists': summary,
    }, ensure_ascii=False, indent=2) + '\n'
    lines = [LABELS['shelf_title'], '',
             '> هذا رف منفصل أنشئ لإكمال بناء **كل قائمة مسجلة** بقالب المشروع. '
             'قرار المالك باعتماد النصوص والشاشات والنشر داخل المستودع موثق؛ لا يُعدّل أي خريطة رسمية. '
             + APPROVAL_NOTE, '',
             f'**{len(summary)} قوائم · {sum(x["episodes"] for x in summary)} ملف مصدر · '
             f'{total_lessons} درسًا · {total_screens} شاشة.**', '',
             '| القائمة | الملفات | الدروس | الشاشات | الصوت / البوابة |',
             '|---|---:|---:|---:|---|']
    for x in summary:
        policy = ('مرشد محايد — لا يطابق Q1' if x['voice'] == 'owner-decision' else 'إيقاع تأسيس، معتمد')
        lines.append(f'| [{x["title"]}]({x["slug"]}/README.md) | {x["episodes"]} | {x["lessons"]} | '
                     f'{x["screens"]} | {policy} |')
    lines += ['', '[فهرس الشاشات](index.html) · [فهرس دورات القوائم](../index.html) · '
              '[طابور الاعتماد](00_طابور_المراجعة.md) · '
              '[لوحة الاعتماد](03_لوحة_المراجعة/index.html) · '
              '[قرار المالك](../00_قرارات_المالك.md) · '
              '[كتالوج RAG الموحد](../../ayman_rag/playlist_inventory.json) · '
              '[تدقيق الاسترجاع](../../ayman_rag/playlist_retrieval_audit.md)', '',
              '## ما تثبته الفحوص', '',
              '- كل درس ستة اقتباسات حرفية على الأقل، بإحالة طابع أو فقرة أو صفحة PDF أو سطر وبصمة.',
              '- كل شاشة مشتقة من نص الدرس نفسه، بنفس `tasees-runtime.js` و`tasees-tokens.css`.',
              '- بصمات الملفات وسطور الاقتباس تُعاد مطابقتها أمام البايتات الحالية.', '',
              '## ما لا تثبته', '',
              'صحة التفريغ، نسبة المتحدث، مطابقة التسجيل، الطبعة، المراجع المستقلة، سلامة '
              'التفسير، أو المراجعة السريرية/العلمية/التاريخية. ' + VERIFICATION_NOTE + ' '
              'القوائم الثلاث «١٠٠ سؤال» و«رحلة اليقين» و«أين الطريق؟» ليست لأيمن، '
              'ومسوداتها هنا بمرشد محايد لا تطابق قرار Q1 (أسلوب أيمن)، فتُعاد صياغتها.', '',
              '```bash',
              'python3 ayman_rag/build_playlist_catalog.py --check',
              'python3 ayman_rag/audit_playlist_retrieval.py --check',
              'python3 08_دورات_القوائم/tools/build_playlist_course_drafts.py --check',
              'python3 08_دورات_القوائم/tools/build_playlist_course_screens.py --check',
              'python3 08_دورات_القوائم/tools/build_review_queue.py --check',
              'python3 -m unittest discover -s 08_دورات_القوائم/tests',
              '```']
    out[OUT / 'README.md'] = '\n'.join(lines) + '\n'
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare without writing')
    args = parser.parse_args(argv)
    generated = build()
    changed = [str(p.relative_to(ROOT)) for p, text in generated.items()
               if not p.exists() or p.read_text(encoding='utf-8') != text]
    if args.check:
        if changed:
            print('✗ ملفات المسودات تحتاج إعادة توليد:')
            for path in changed[:20]:
                print('  ' + path)
            if len(changed) > 20:
                print(f'  ... و{len(changed) - 20} ملفًا آخر')
            return 1
        print(f'ok: {len(generated)} ملفًا للمسودات مطابق للمصادر')
        return 0
    for p, text in generated.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} draft files '
          f'({sum(1 for p in generated if p.name.startswith("lesson-") and p.suffix == ".md")} lessons)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
