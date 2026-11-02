#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني شاشات الدروس التفاعلية وفهارسها من نصوص الدروس نفسها.

    python3 08_دورات_القوائم/tools/build_lesson_screens.py           # كتابة
    python3 08_دورات_القوائم/tools/build_lesson_screens.py --check    # فحص بلا كتابة

القالب مشتق آليًا من `07_الهوية_البصرية_والتفاعل/templates/week-template.html`
(نفس CSS و`tasees-runtime.js`)، مع تبديل «الأسبوع» إلى «الدرس»، وإضافة شريط
«معتمد من المالك» ورابط نص الدرس. المحتوى يُقرأ من `01_نصوص_الدروس/lesson-NN.md`
لا من ذاكرة: الاقتباسات والشواهد والأدوات والمهمات تُستخرج من النص، فلا تدخل
الشاشة معلومة ليست في الدرس. الشاشات معتمدة من المالك مع قيود تحقق موثقة.

الأنماط المستعملة: P14 (توقّع)، P02 (فرز)، P17 (بطاقات)، P15 (الدفتر).
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from owner_decisions import LABELS, SHORT_STATUS, status  # noqa: E402

PKG = HERE.parent
ROOT = PKG.parent
WEEK_TEMPLATE = ROOT / '07_الهوية_البصرية_والتفاعل' / 'templates' / 'week-template.html'
SHARED_REL = Path('07_الهوية_البصرية_والتفاعل') / 'templates'
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

COURSES = [
    dict(key='l1', folder='التأسيس_المعرفي/المستوى_الأول', label='التأسيس المعرفي — المستوى الأول',
         slug='cf1', count=8, note='ثمانية ملفات Drive، درس لكل ملف. معتمد من المالك؛ الخريطة الرسمية لم تُعدّل.'),
    dict(key='l2', folder='التأسيس_المعرفي/المستوى_الثاني', label='التأسيس المعرفي — المستوى الثاني',
         slug='cf2', count=7, note='سبعة ملفات Drive؛ السادس والسابع يظلان منفصلين.'),
    dict(key='psy', folder='علم_النفس', label='علم النفس — المسار الموازي', slug='psy',
         count=10, note='مسار موازٍ معتمد من المالك على تفريغات Drive؛ الدروس الأساسية محفوظة دون تعديل.'),
]

TRACKS = ('مستكشف', 'ممارس', 'متقدم')
PATTERNS = {'P02', 'P14', 'P15', 'P17'}


def sections(text: str) -> dict[str, str]:
    out = {}
    parts = re.split(r'^##\s+', text, flags=re.M)
    for p in parts[1:]:
        name, _, body = p.partition('\n')
        out[name.strip()] = body.strip()
    return out


def one_line(s: str, limit: int = 260) -> str:
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= limit else s[:limit].rsplit(' ', 1)[0] + '…'


def parse_lesson(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    n = int(path.stem[-2:])
    title_m = re.match(r'^#\s*الدرس\s+\S+\s+—\s+(.+)$', text, re.M)
    title = title_m.group(1).strip() if title_m else path.stem
    sec = sections(text)
    sha_m = re.search(r'SHA-256\s+`([0-9a-f]{64})`', text)
    sha = sha_m.group(1) if sha_m else ''
    link_m = re.search(r'\[التفريغ النصي للحلقة \d+\]\(([^)]+)\)', text)
    source_link = link_m.group(1) if link_m else ''
    hook = sec.get('افتتاح وخطاف', '')
    hook_par = next((p for p in hook.split('\n\n') if p.strip()), '')
    cut = re.search(r'[؟.!]\s', hook_par)
    voice = hook_par[:cut.end()].strip() if cut else one_line(hook_par, 90)
    sharh = hook_par[cut.end():].strip() if cut else ''
    blocks = []
    for label in ('الكتلة ١', 'الكتلة ٢', 'الكتلة ٣'):
        key = next((k for k in sec if k.startswith(label)), None)
        body = sec.get(key, '') if key else ''
        heading = key.strip() if key else label
        quotes = re.findall(r'«([^»]+)»\s*〔ح(\d+)\s+س([٠-٩\d]+)(?:-([٠-٩\d]+))?\s+sha256=[0-9a-f]{64}〕', body)
        tool = re.search(r'\*\*أداة الكتلة:\s*([^*]+)\.\*\*\s*(.+)', body)
        intro = body.split('\n\n')[0] if body else ''
        discussion = ''
        dm = re.search(r'\n\n([^\n]+)\n\nودي أداة', body)
        if dm:
            discussion = dm.group(1)
        blocks.append(dict(heading=heading, quotes=quotes,
                           tool_name=tool.group(1).strip() if tool else 'أداة الدرس',
                           tool_text=one_line(tool.group(2) if tool else body, 150),
                           intro=one_line(intro, 240), discussion=one_line(discussion, 200)))
    tasks = {}
    for t in TRACKS:
        m = re.search(r'\*\*' + t + r':\*\*\s*(.+)', sec.get('المهمة', ''))
        tasks[t] = one_line(m.group(1), 220) if m else 'راجع نص الدرس.'
    trap = one_line(sec.get('مصيدة الفهم', '').split('\n')[0], 200)
    close = sec.get('القفلة', '')
    next_m = re.search(r'الدرس الجاي\s+(.+?)\s+استنى هناك', close, re.S)
    next_text = one_line(next_m.group(1), 160) if next_m else 'الدرس التالي بعد المراجعة.'
    closing_line = one_line(close.split('\n')[0], 160)
    return dict(n=n, title=title, question=one_line(sec.get('سؤال الدرس', ''), 200),
                voice=voice, sharh=one_line(sharh, 260) or 'نقرأ الدرس بسؤال واحد وثلاث كتل.',
                sha=sha, source_link=source_link, blocks=blocks, tasks=tasks, trap=trap,
                next=next_text, closing=closing_line)


def make_screens(c: dict, L: dict) -> list[dict]:
    n, slug = L['n'], c['slug']
    ids = lambda k: f'{slug}-l{n:02d}-{k:02d}'
    sanad_base = [['الدرس ' + str(n).translate(AR), 'ملف واحد'], ['السند', 'سطور + SHA-256']]
    quotes_all = [(q, ep, s, e) for b in L['blocks'] for q, ep, s, e in b['quotes']]
    screen = lambda k, **kw: dict(id=ids(k), **kw)

    def block_screen(k, b, idx, with_trap=False):
        sq = b['quotes'][:2]
        labels = [[f'ح{ep}', f'س{s}' + (f'-{e}' if e else '')] for _, ep, s, e in sq]
        matn = '«' + sq[0][0] + '»' if sq else b['intro']
        sharh = ' '.join(x for x in (b['intro'], b['discussion']) if x)
        d = dict(layout='L3', heading=b['heading'], matn=matn,
                 sharh=one_line(sharh, 320), sanad=sanad_base + labels)
        if with_trap:
            d['trap'] = dict(title='مصيدة الفهم', text=L['trap'])
        return screen(k, **d)

    items = []
    for q, ep, s, e in quotes_all[:3]:
        items.append([one_line(q, 42), 0])
    items.append([one_line(L['trap'], 42), 1])
    items.append([one_line(L['blocks'][0]['tool_name'], 42), 2])

    lines = [L['closing'],
             'ثلاث أدوات: ' + ' · '.join(b['tool_name'] for b in L['blocks']),
             SHORT_STATUS + ': الاقتباس يثبت الموضع، والتسجيل والمراجع قيود موثقة.']
    return [
        screen(1, layout='L1', sanad=sanad_base),
        screen(2, layout='L2', art=f'rasms-al-khattaf-{slug}-l{n:02d}', art_src='',
               sanad=[['الافتتاح', 'مثال تعليمي']], voice=L['voice'], sharh=L['sharh']),
        screen(3, layout='L4', pattern='P14', heading='قبل ما نبدأ',
               instruction='اختر توقّعًا واحدًا؛ سنعود إليه في القفلة.', sanad=[['سؤال الدرس', 'توقّع']],
               data=dict(q='ما الذي تتوقع أن يثبته هذا الدرس من الملف؟',
                         options=['إحالات واقتباسات قابلة للفحص', 'أحكامًا نهائية عن الموضوع',
                                  'لا أعلم بعد — أحتاج قراءة المصدر'],
                         saved='اتسجلت. نرجع لها في القفلة.')),
        block_screen(4, L['blocks'][0], 1),
        screen(5, layout='L4', pattern='P02', heading='نص، أم لبس، أم أداة؟',
               instruction='اختر العبارة ثم السلة.', sanad=[['الدرس', 'فرز المادة']],
               data=dict(bins=['منقول من المصدر', 'لبس شائع', 'أداة أضافها الدرس'], items=items,
                         done='الفرز بين النص والتفسير أول خطوة في المراجعة.')),
        block_screen(6, L['blocks'][1], 2),
        screen(7, layout='L4', pattern='P17', heading='بطاقات أدوات الدرس',
               instruction='اقلب كل بطاقة لتقرأ وصف الأداة.', sanad=[['الكتل الثلاث', 'أدوات']],
               data=dict(cards=[[b['tool_name'], b['tool_text']] for b in L['blocks']])),
        block_screen(8, L['blocks'][2], 3, with_trap=True),
        screen(9, layout='L6', pattern='P15', sanad=[['الدفتر', 'مهمة الدرس']],
               data=dict(q='ما الذي أخذته من الدرس، وما الذي أجّلته للمراجعة؟',
                         key=f'journal-{slug}-l{n:02d}')),
        screen(10, layout='L7', heading='نلمّ الدرس في تلات سطور', sanad=sanad_base,
               lines=lines,
               replay='في الأول اخترت {{predict}}. والآن: الاقتباس يثبت الموضع لا المعنى.',
               task=dict(zip(TRACKS, (L['tasks'][t] for t in TRACKS)))),
    ]


def lesson_json(c: dict, L: dict) -> dict:
    return dict(week=L['n'], lesson=L['n'], course=c['label'], source_sha=L['sha'],
                eyebrow=f'{c["label"]} · الدرس {str(L["n"]).translate(AR)}',
                title=L['title'], subtitle='درس من ملف واحد · ' + status(),
                question=L['question'],
                audio='لا تسجيل متحقق مرتبط بهذا الدرس؛ الاقتباسات من تفريغ نصي آلي، وأرقام السطور ليست توقيتات.',
                next='الدرس الجاي ' + L['next'],
                text_href=f'../01_نصوص_الدروس/lesson-{L["n"]:02d}.md',
                draft=status() + ' — ' + LABELS['verification_note'],
                screens=make_screens(c, L))


def lesson_template() -> str:
    """شتقّ قالب الدرس من قالب الأسبوع، مع أقل تعديل ممكن في البنية."""
    t = WEEK_TEMPLATE.read_text(encoding='utf-8')
    t = t.replace('data-week="w01"', 'data-week="{{WEEK_ID}}"')
    t = t.replace('data-root="../../"', 'data-root="{{ROOT}}"')
    t = re.sub(r'<title>.*?</title>', '<title>{{TITLE}}</title>', t, count=1, flags=re.S)
    t = re.sub(r'<link rel="stylesheet" href="[^"]*tasees-tokens\.css">',
               '<link rel="stylesheet" href="{{SHARED}}tasees-tokens.css">', t, count=1)
    t = t.replace('<link rel="stylesheet" href="tasees-tokens.css">\n', '')
    t = re.sub(r'<script src="[^"]*atlas-course-bundle\.js" onerror="this\.remove\(\)"></script>',
               '<script src="{{SHARED}}atlas-course-bundle.js" onerror="this.remove()"></script>', t, count=1)
    t = t.replace('<script src="atlas-course-bundle.js" onerror="this.remove()"></script>\n', '')
    t = re.sub(r'<script src="[^"]*templates/tasees-runtime\.js" onerror="this\.remove\(\)"></script>',
               '<script src="{{SHARED}}tasees-runtime.js"></script>', t)
    t = t.replace('<script src="tasees-runtime.js"></script>\n', '')
    t = re.sub(r'(<script type="application/json" id="week">\n).*?(\n</script>)',
               r'\1{{JSON}}\2', t, count=1, flags=re.S)
    # بيانات الشاشة: «الدرس» بدل «الأسبوع»، وشريط الاعتماد، ورابط نص الدرس.
    t = t.replace('<small>سؤال الأسبوع</small>', '<small>سؤال الدرس</small>')
    t = t.replace('· الأسبوع ', '· الدرس ')
    t = t.replace('محتوى الأسبوع', 'محتوى الدرس')
    t = t.replace('مهمة الأسبوع · ', 'مهمة الدرس · ')
    l1_tail = ("'<div class=\"audio\">' + esc(W.audio) + '</div>' + "
               "'<p class=\"t-feedback t-feedback--bad\"><strong>معتمد</strong>' + esc(W.draft) + '</p>' + "
               "'<p class=\"t-small\" style=\"margin:0\"><a href=\"' + esc(W.text_href) + '\">اقرأ نص الدرس كاملًا ←</a></p>' + "
               "'<p class=\"t-small\" style=\"margin:0\">معتمد من المالك؛ لا تُنسب عباراتها لصاحب التسجيل قبل التحقق.</p>';")
    t, count = re.subn(r"'<div class=\"audio\">'.*?</p>';", lambda m: l1_tail, t, count=1, flags=re.S)
    assert count == 1, 'L1 audio tail not found in week-template.html' 
    t = re.sub(r'<!--.*?-->', '<!-- قالب شاشة الدرس: مشتق من week-template.html، بنفس CSS وtasees-runtime.js. '
               'عدّل المحتوى في 01_نصوص_الدروس ثم أعد build_lesson_screens.py. -->', t, count=1, flags=re.S)
    for token in ('{{WEEK_ID}}', '{{ROOT}}', '{{TITLE}}', '{{SHARED}}', '{{JSON}}'):
        assert token in t, f'missing template token {token}'
    return t


def render_page(c: dict, L: dict, tpl: str, screen_dir: Path) -> str:
    rootrel = Path(os.path.relpath(ROOT, screen_dir)).as_posix() + '/'
    shared = (rootrel.rstrip('/') + '/' + SHARED_REL.as_posix() + '/')
    page = (tpl.replace('{{ROOT}}', rootrel)
               .replace('{{SHARED}}', shared)
               .replace('{{WEEK_ID}}', f'{c["slug"]}-l{L["n"]:02d}')
               .replace('{{TITLE}}', html.escape('تأسيس · ' + L['title'])))
    data = json.dumps(lesson_json(c, L), ensure_ascii=False, indent=1)
    return page.replace('{{JSON}}', data)


def index_page(title: str, intro: str, rows: list[tuple[str, str]], rootrel: str, back: str | None) -> str:
    items = '\n'.join(
        f'      <li><a href="{html.escape(href)}">{html.escape(label)}</a></li>' for label, href in rows)
    backlink = (f'<p><a href="{html.escape(back)}">← فهرس دورات القوائم</a></p>' if back else '')
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{rootrel}07_الهوية_البصرية_والتفاعل/templates/tasees-tokens.css">
<style>body{{margin:0}}main{{max-width:var(--stage-max);margin:0 auto;padding:24px 16px}}li{{margin:8px 0;line-height:1.8}}</style>
</head>
<body class="t-page">
<main>
  <p class="t-eyebrow">دورات القوائم · معتمدة من المالك</p>
  <h1 class="t-title">{html.escape(title)}</h1>
  <p class="t-sharh">{html.escape(intro)}</p>
  {backlink}
  <ol class="lines">
{items}
  </ol>
  <p class="t-feedback"><strong>تنبيه:</strong> الشاشات والنصوص معتمدة من المالك بقرار موثق؛ الاقتباسات من تفريغ آلي،
  والمتحدث والتسجيل والطبعة والمراجع قيود غير متحققة آليًا. لا تشخيص ولا نصيحة علاجية في علم النفس،
  ولا أحكام تاريخية أو طائفية في التأسيس المعرفي.</p>
</main>
</body>
</html>
'''


def validate(c: dict, L: dict, data: dict) -> None:
    assert data['source_sha'] == L['sha'] and len(data['source_sha']) == 64, 'source_sha mismatch'
    sc = data['screens']
    assert 10 <= len(sc) <= 13, 'screen count'
    assert sc[0]['layout'] == 'L1' and sc[-1]['layout'] == 'L7', 'first/last layout'
    assert set(sc[-1]['task']) == set(TRACKS) and len(sc[-1]['lines']) == 3, 'closing data'
    for s in sc:
        assert s['id'] and s['layout'] in {'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7'}, s['id']
        assert s.get('sanad'), s['id'] + ': missing sanad'
        if s.get('pattern'):
            assert s['pattern'] in PATTERNS and isinstance(s.get('data'), dict), s['id']
    patterns = [s['pattern'] for s in sc if s.get('pattern')]
    assert len([p for p in patterns if p not in ('P14', 'P15')]) >= 2, 'interactive patterns'
    assert all(b['quotes'] and b['tool_name'] for b in L['blocks']), 'parsed lesson content'


def build() -> dict[Path, str]:
    tpl = lesson_template()
    out: dict[Path, str] = {}
    hub_rows = []
    for c in COURSES:
        course_dir = PKG / c['folder']
        lessons_dir = course_dir / '01_نصوص_الدروس'
        screen_dir = course_dir / '02_الشاشات'
        lessons = sorted(lessons_dir.glob('lesson-[0-9][0-9].md'))
        assert len(lessons) == c['count'], f'{c["key"]}: expected {c["count"]} lessons, found {len(lessons)}'
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
        hub = Path(os.path.relpath(PKG / 'index.html', screen_dir)).as_posix()
        out[screen_dir / 'index.html'] = index_page(
            c['label'] + ' — فهرس الشاشات',
            c['note'] + f' {len(lessons)} درسًا، لكل درس عشر شاشات تفاعلية ونصه الكامل.',
            idx_rows, idx_root, hub)
        hub_rows.append((f'{c["label"]} — {len(lessons)} درسًا',
                         f'{c["folder"]}/02_الشاشات/index.html'))
    hub_rows.append(('دورات القوائم — إحدى عشرة قائمة', '10_مسودات_القوائم/index.html'))
    out[PKG / 'index.html'] = index_page(
        'دورات القوائم — دروس وشاشات معتمدة من المالك',
        'ثلاثة مسارات مكتوبة بقالب المشروع: التأسيس المعرفي بمستوييه، والمسار الموازي لعلم النفس، '
        'إلى جانب رف معتمد يغطي كل قوائم التشغيل المسجلة. كل درس له نص محقق السند '
        'وشاشات تفاعلية مبنية منه، وقرار المالك موثق مع قيود التحقق.',
        hub_rows, '../', None)
    return out


def main(argv: list[str]) -> int:
    generated = build()
    check = '--check' in argv
    changed = [str(p.relative_to(ROOT)) for p, text in generated.items()
               if not p.exists() or p.read_text(encoding='utf-8') != text]
    if check:
        if changed:
            print('✗ ملفات تحتاج إعادة توليد:')
            for c in changed:
                print('  ' + c)
            return 1
        print(f'ok: {len(generated)} ملفًا (شاشات + فهارس) مطابق للنصوص')
        return 0
    for p, text in generated.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} files ({sum(1 for p in generated if p.suffix == ".html" and p.name.startswith("lesson-"))} lesson screens)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
