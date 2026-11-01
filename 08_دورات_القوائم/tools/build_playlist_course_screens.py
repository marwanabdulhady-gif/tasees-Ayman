#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate ten interactive screens per all-playlist course draft.

    python3 08_دورات_القوائم/tools/build_playlist_course_screens.py
    python3 08_دورات_القوائم/tools/build_playlist_course_screens.py --check

Every screen is derived from ``week-template.html`` and the generated lesson
Markdown, using the same ``tasees-tokens.css`` and ``tasees-runtime.js``. No
independent factual content is introduced. The screen JSON records the lesson's
source IDs, SHA-256 fingerprints, local source links and episode numbers for
audit. Everything remains an unapproved draft pending owner review.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_lesson_screens as base  # noqa: E402
from playlist_sources import PKG, ROOT  # noqa: E402

OUT = PKG / '10_مسودات_القوائم'
STATE = OUT / '00_حالة_القوائم.json'
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
AR2EN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
QUOTE_CITE = re.compile(r'«([^»]+)»\s*〔([^〕]+)〕')
TRACKS = base.TRACKS
PATTERNS = base.PATTERNS
one_line = base.one_line
sections = base.sections


def parse_citation(cite: str):
    m = re.match(r'ح([٠-٩\d]+)\s+س([٠-٩\d]+)(?:-([٠-٩\d]+))?\s+sha256=', cite)
    if m:
        ep = int(m.group(1).translate(AR2EN))
        label = 'س' + m.group(2) + (('-' + m.group(3)) if m.group(3) else '')
        return ep, label, 'line'
    m = re.match(r'ح([٠-٩\d]+)\s+(\d{1,2}:\d{2}(?::\d{2})?)', cite)
    if m:
        return int(m.group(1).translate(AR2EN)), m.group(2), 'timestamp'
    m = re.match(r'ح([٠-٩\d]+)\s+ف([٠-٩\d]+)', cite)
    if m:
        return int(m.group(1).translate(AR2EN)), 'ف' + m.group(2), 'paragraph'
    raise ValueError(f'unsupported lesson citation: {cite}')


def parse_lesson(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    n = int(path.stem.split('-')[-1])
    title_m = re.match(r'^#\s*الدرس\s+\S+\s+—\s+(.+)$', text, re.M)
    title = title_m.group(1).strip() if title_m else path.stem
    sec = sections(text)
    shas = re.findall(r'SHA-256\s+`([0-9a-f]{64})`', text)
    source_ids = re.findall(r'معرّف المصدر `([^`]+)`', text)
    source_links = re.findall(r'\[التفريغ النصي للحلقة [^\]]+\]\(([^)]+)\)', text)
    episodes = [int(x.translate(AR2EN)) for x in
                re.findall(r'\[التفريغ النصي للحلقة ([٠-٩\d]+)\]', text)]
    if not shas or len(shas) != len(source_ids) or len(shas) != len(source_links):
        raise ValueError(f'{path}: source metadata count mismatch')
    catalog_sha = hashlib.sha256('\n'.join(shas).encode('utf-8')).hexdigest()
    hook = sec.get('افتتاح وخطاف', '')
    hook_par = next((p for p in hook.split('\n\n') if p.strip()), '')
    cut = re.search(r'[؟.!]\s', hook_par)
    voice = hook_par[:cut.end()].strip() if cut else one_line(hook_par, 90)
    sharh = hook_par[cut.end():].strip() if cut else ''
    blocks = []
    for label in ('الكتلة ١', 'الكتلة ٢', 'الكتلة ٣'):
        key = next((k for k in sec if k.startswith(label)), None)
        body = sec.get(key, '') if key else ''
        quotes = []
        for m in QUOTE_CITE.finditer(body):
            ep, cite_label, kind = parse_citation(m.group(2))
            quotes.append((m.group(1), ep, cite_label, kind))
        tool = re.search(r'\*\*أداة الكتلة:\s*([^*]+)\.\*\*\s*(.+)', body)
        intro = body.split('\n\n')[0] if body else ''
        dm = re.search(r'\n\n([^\n]+)\n\nودي نقطة عملية', body)
        blocks.append(dict(heading=key.strip() if key else label, quotes=quotes,
                           tool_name=tool.group(1).strip() if tool else 'أداة الدرس',
                           tool_text=one_line(tool.group(2) if tool else body, 150),
                           intro=one_line(intro, 240),
                           discussion=one_line(dm.group(1) if dm else '', 200)))
    tasks = {}
    for t in TRACKS:
        m = re.search(r'\*\*' + t + r':\*\*\s*(.+)', sec.get('المهمة', ''))
        tasks[t] = one_line(m.group(1), 220) if m else 'راجع نص الدرس.'
    trap = one_line(sec.get('مصيدة الفهم', '').split('\n')[0], 200)
    close = sec.get('القفلة', '')
    next_m = re.search(r'الدرس الجاي\s+(.+?)\s+استنى هناك', close, re.S)
    next_text = one_line(next_m.group(1), 160) if next_m else 'الدرس التالي بعد المراجعة.'
    kinds = sorted({kind for b in blocks for *_, kind in b['quotes']})
    return dict(n=n, title=title, question=one_line(sec.get('سؤال الدرس', ''), 200),
                voice=voice, sharh=one_line(sharh, 260) or 'نقرأ الدرس بسؤال واحد وثلاث كتل.',
                catalog_sha=catalog_sha, source_shas=shas, source_ids=source_ids,
                source_links=source_links, episodes=episodes, citation_kinds=kinds,
                blocks=blocks, tasks=tasks, trap=trap, next=next_text,
                closing=one_line(close.split('\n')[0], 160))


def make_screens(c: dict, L: dict) -> list[dict]:
    n, slug = L['n'], c['slug']
    ids = lambda k: f'{slug}-l{n:02d}-{k:02d}'
    sanad_base = [['الدرس ' + str(n).translate(AR), f'{len(L["source_ids"])} مصدر'],
                  ['السند', 'إحالة + بصمة']]
    quotes_all = [(q, ep, label) for b in L['blocks'] for q, ep, label, _ in b['quotes']]
    screen = lambda k, **kw: dict(id=ids(k), **kw)

    def block_screen(k, b, with_trap=False):
        sq = b['quotes'][:2]
        labels = [[f'ح{ep}', label] for _, ep, label, _ in sq]
        matn = '«' + sq[0][0] + '»' if sq else b['intro']
        sharh = ' '.join(x for x in (b['intro'], b['discussion']) if x)
        d = dict(layout='L3', heading=b['heading'], matn=matn,
                 sharh=one_line(sharh, 320), sanad=sanad_base + labels)
        if with_trap:
            d['trap'] = dict(title='مصيدة الفهم', text=L['trap'])
        return screen(k, **d)

    items = [[one_line(q, 42), 0] for q, _, _ in quotes_all[:3]]
    items.append([one_line(L['trap'], 42), 1])
    items.append([one_line(L['blocks'][0]['tool_name'], 42), 2])
    lines = [L['closing'],
             'ثلاث أدوات: ' + ' · '.join(b['tool_name'] for b in L['blocks']),
             'مسودة غير معتمدة: الاقتباس يثبت الموضع، والتسجيل والمراجع يثبتان الباقي.']
    return [
        screen(1, layout='L1', sanad=sanad_base),
        screen(2, layout='L2', art=f'rasms-al-khattaf-{slug}-l{n:02d}', art_src='',
               sanad=[['الافتتاح', 'مثال تعليمي']], voice=L['voice'], sharh=L['sharh']),
        screen(3, layout='L4', pattern='P14', heading='قبل ما نبدأ',
               instruction='اختر توقّعًا واحدًا؛ سنعود إليه في القفلة.', sanad=[['سؤال الدرس', 'توقّع']],
               data=dict(q='ما الذي تتوقع أن يثبته هذا الدرس من ملفات القائمة؟',
                         options=['إحالات واقتباسات قابلة للفحص', 'أحكامًا نهائية عن الموضوع',
                                  'لا أعلم بعد — أحتاج قراءة المصدر'],
                         saved='اتسجلت. نرجع لها في القفلة.')),
        block_screen(4, L['blocks'][0]),
        screen(5, layout='L4', pattern='P02', heading='نص، أم لبس، أم أداة؟',
               instruction='اختر العبارة ثم السلة.', sanad=[['الدرس', 'فرز المادة']],
               data=dict(bins=['منقول من المصدر', 'لبس شائع', 'أداة أضافها الدرس'], items=items,
                         done='الفرز بين النص والتفسير أول خطوة في المراجعة.')),
        block_screen(6, L['blocks'][1]),
        screen(7, layout='L4', pattern='P17', heading='بطاقات أدوات الدرس',
               instruction='اقلب كل بطاقة لتقرأ وصف الأداة.', sanad=[['الكتل الثلاث', 'أدوات']],
               data=dict(cards=[[b['tool_name'], b['tool_text']] for b in L['blocks']])),
        block_screen(8, L['blocks'][2], with_trap=True),
        screen(9, layout='L6', pattern='P15', sanad=[['الدفتر', 'مهمة الدرس']],
               data=dict(q='ما الذي أخذته من الدرس، وما الذي أجّلته للمراجعة؟',
                         key=f'journal-{slug}-l{n:02d}')),
        screen(10, layout='L7', heading='نلمّ الدرس في تلات سطور', sanad=sanad_base,
               lines=lines,
               replay='في الأول اخترت {{predict}}. والآن: الاقتباس يثبت الموضع لا المعنى.',
               task=dict(zip(TRACKS, (L['tasks'][t] for t in TRACKS)))),
    ]


def lesson_json(c: dict, L: dict) -> dict:
    return dict(week=L['n'], lesson=L['n'], course=c['label'],
                source_sha=L['catalog_sha'], source_shas=L['source_shas'],
                source_ids=L['source_ids'], source_links=L['source_links'],
                episodes=L['episodes'], citation_kinds=L['citation_kinds'],
                eyebrow=f'{c["label"]} · الدرس {str(L["n"]).translate(AR)}',
                title=L['title'], subtitle='درس من حلقات القائمة · مسودة تعليمية غير معتمدة',
                question=L['question'],
                audio='لا تسجيل متحقق مرتبط بهذا الدرس؛ الطوابع أو الفقرات أو السطور مواضع نصية غير مؤكدة من التسجيل.',
                next='الدرس الجاي ' + L['next'],
                text_href=f'../01_نصوص_الدروس/lesson-{L["n"]:02d}.md',
                draft='مسودة تعليمية غير معتمدة — راجع التسجيل والمراجع قبل النشر.',
                screens=make_screens(c, L))


def render_page(c: dict, L: dict, tpl: str, screen_dir: Path) -> str:
    rootrel = Path(os.path.relpath(base.ROOT, screen_dir)).as_posix() + '/'
    shared = rootrel.rstrip('/') + '/' + base.SHARED_REL.as_posix() + '/'
    page = (tpl.replace('{{ROOT}}', rootrel)
               .replace('{{SHARED}}', shared)
               .replace('{{WEEK_ID}}', f'{c["slug"]}-l{L["n"]:02d}')
               .replace('{{TITLE}}', html.escape('تأسيس · ' + L['title'])))
    data = json.dumps(lesson_json(c, L), ensure_ascii=False, indent=1)
    return page.replace('{{JSON}}', data)


def validate(c: dict, L: dict, data: dict) -> None:
    assert data['source_sha'] == L['catalog_sha'] and len(data['source_sha']) == 64
    assert data['source_ids'] == L['source_ids'] and data['source_shas'] == L['source_shas']
    assert data['episodes'] == L['episodes'] and len(data['screens']) == 10
    sc = data['screens']
    assert sc[0]['layout'] == 'L1' and sc[-1]['layout'] == 'L7'
    assert set(sc[-1]['task']) == set(TRACKS) and len(sc[-1]['lines']) == 3
    for s in sc:
        assert s['id'] and s['layout'] in {'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7'}, s['id']
        assert s.get('sanad'), s['id'] + ': missing sanad'
        if s.get('pattern'):
            assert s['pattern'] in PATTERNS and isinstance(s.get('data'), dict), s['id']
    patterns = [s['pattern'] for s in sc if s.get('pattern')]
    assert len([p for p in patterns if p not in ('P14', 'P15')]) >= 2
    assert all(b['quotes'] and b['tool_name'] for b in L['blocks']), 'parsed lesson content'
    assert len([q for b in L['blocks'] for q in b['quotes']]) >= 6


def build() -> dict[Path, str]:
    state = json.loads(STATE.read_text(encoding='utf-8'))
    tpl = base.lesson_template()
    out: dict[Path, str] = {}
    hub_rows = []
    for summary in state['playlists']:
        slug = summary['slug']
        c = dict(key=slug, folder=f'10_مسودات_القوائم/{slug}', label=summary['title'],
                 slug=slug, count=summary['lessons'],
                 note='مسودة غير معتمدة؛ دروس مولّدة من ملفات القائمة بقالب المشروع.')
        course_dir = OUT / slug
        lessons_dir = course_dir / '01_نصوص_الدروس'
        screen_dir = course_dir / '02_الشاشات'
        lessons = sorted(lessons_dir.glob('lesson-[0-9][0-9].md'))
        assert len(lessons) == c['count'], f'{slug}: expected {c["count"]} lessons, found {len(lessons)}'
        idx_rows = []
        for path in lessons:
            L = parse_lesson(path)
            data = lesson_json(c, L)
            validate(c, L, data)
            out[screen_dir / f'lesson-{L["n"]:02d}.html'] = render_page(c, L, tpl, screen_dir)
            idx_rows.append((f'الدرس {str(L["n"]).translate(AR)} — {L["title"]} · الشاشات',
                             f'lesson-{L["n"]:02d}.html'))
            idx_rows.append((f'↳ نص الدرس {str(L["n"]).translate(AR)} (Markdown)',
                             f'../01_نصوص_الدروس/lesson-{L["n"]:02d}.md'))
        idx_root = Path(os.path.relpath(ROOT, screen_dir)).as_posix() + '/'
        hub = Path(os.path.relpath(OUT / 'index.html', screen_dir)).as_posix()
        out[screen_dir / 'index.html'] = base.index_page(
            c['label'] + ' — فهرس الشاشات',
            c['note'] + f' {len(lessons)} درسًا، لكل درس عشر شاشات تفاعلية ونصه الكامل.',
            idx_rows, idx_root, hub)
        hub_rows.append((f'{c["label"]} — {len(lessons)} درسًا', f'{slug}/02_الشاشات/index.html'))
    rootrel = Path(os.path.relpath(ROOT, OUT)).as_posix() + '/'
    out[OUT / 'index.html'] = base.index_page(
        'مسودات قوائم التشغيل — فهرس الشاشات',
        'عشر قوائم مسجلة في قالب المشروع. كل درس له نص محقق السند وعشر شاشات مبنية من النص. '
        'هذه مسودات غير معتمدة، ولا تُقرأ بوصفها خرائط رسمية أو محتوى منشورًا.',
        hub_rows, rootrel, '../index.html')
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
            print('✗ شاشات المسودات تحتاج إعادة توليد:')
            for path in changed[:20]:
                print('  ' + path)
            if len(changed) > 20:
                print(f'  ... و{len(changed) - 20} ملفًا آخر')
            return 1
        print(f'ok: {len(generated)} ملف شاشات/فهارس مطابق للنصوص')
        return 0
    for p, text in generated.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} files '
          f'({sum(1 for p in generated if p.name.startswith("lesson-") and p.suffix == ".html")} lesson screens)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
