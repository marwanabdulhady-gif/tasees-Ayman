#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يولّد فهرس المسار الموازي لعلم النفس من ملفات الدروس وسجل Drive.

    python3 08_دورات_القوائم/tools/build_parallel_track_index.py
    python3 08_دورات_القوائم/tools/build_parallel_track_index.py --check

الفهرس يبقى منفصلًا عن `00_خريطة_الدورة.json` (حالتها «نصوص بلا خريطة»)،
ولا يُدمج فيه التفريغ القديم بنسخة Drive. قرار المالك باعتماد الدروس موثق،
لكنه لا يثبت التسجيل أو المراجع آليًا. كل سطر يتحقق من بصمة المصدر وعدد
الإحالات في الدرس قبل كتابته.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from owner_decisions import LABELS, SHORT_STATUS, status  # noqa: E402

PKG = HERE.parent
ROOT = PKG.parent
COURSE = PKG / 'علم_النفس'
OUT = COURSE / '01_فهرس_المسودة_الموازية.md'
INVENTORY = ROOT / '09_تفريغات_أيمن' / 'drive_inventory.json'
FOLDER = 'دورة-علم-النفس-م-أيمن-عبد-الرحيم'
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def build() -> str:
    docs = json.loads(INVENTORY.read_text(encoding='utf-8'))['documents']
    by_file = {}
    for d in docs:
        if FOLDER in d['path']:
            n = int(re.match(r'^(\d+)', Path(d['path']).name).group(1))
            by_file[n] = d
    lessons = sorted((COURSE / '01_نصوص_الدروس').glob('lesson-[0-9][0-9].md'))
    rows, cite_total = [], 0
    for p in lessons:
        n = int(p.stem[-2:])
        text = p.read_text(encoding='utf-8')
        d = by_file[n]
        source = ROOT / d['path']
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if sha != d['sha256']:
            raise ValueError(f'{d["path"]}: SHA-256 mismatch')
        link = re.search(r'\[التفريغ النصي للحلقة \d+\]\(([^)]+)\)', text)
        if not link or f'lesson-{n:02d}' not in p.name:
            raise ValueError(f'{p}: missing source link')
        cites = re.findall(r'〔ح(\d+) س[٠-٩\d]+(?:-[٠-٩\d]+)? sha256=([0-9a-f]{64})〕', text)
        if len(cites) < 6 or any(int(ep) != n or h != sha for ep, h in cites):
            raise ValueError(f'{p}: citations do not match source {n}')
        cite_total += len(cites)
        title = re.match(r'^#\s*الدرس\s+\S+\s+—\s+(.+)$', text, re.M).group(1).strip()
        screen = COURSE / '02_الشاشات' / f'lesson-{n:02d}.html'
        if not screen.exists():
            raise ValueError(f'{screen}: missing screen')
        rows.append(f'| {str(n).translate(AR)} | [{title}](01_نصوص_الدروس/lesson-{n:02d}.md) · '
                    f'[الشاشات](02_الشاشات/lesson-{n:02d}.html) | `{d["id"]}` | `{sha[:12]}` | '
                    f'{len(cites)} |')
    unused = sorted(set(by_file) - {int(p.stem[-2:]) for p in lessons})
    unused_rows = '\n'.join(f'- الملف `{str(n).translate(AR)}` — `{by_file[n]["id"]}` — '
                            f'{Path(by_file[n]["path"]).name}: لم يُكتب له درس في هذا المسار؛ '
                            'يُترك لمراجعة مستقلة، ولا يُدمج مع غيره.' for n in unused)
    return f'''# فهرس المسار الموازي — علم النفس (تفريغات Drive)

**الحالة:** {status()} · **الدروس:** {str(len(lessons)).translate(AR)} · \
**الإحالات المحققة:** {str(cite_total).translate(AR)} · **المصدر:** ملفات Drive النصية، كل درس من ملف واحد.

هذا فهرس **مسار موازٍ معتمد من المالك**، لا خريطة رسمية. {LABELS['publication_note']}
الخريطة الرسمية [`00_خريطة_الدورة.json`](00_خريطة_الدورة.json) حالتها «نصوص بلا خريطة»، والدروس الأساسية في
[`الدروس/`](الدروس/) والمسودة القصيرة في [`مسودات_الدروس/`](مسودات_الدروس/) محفوظتان دون تعديل.
لا تُنقل توقيتات التفريغ القديم إلى نسخ Drive، ولا تُدمج النسخ المتشابهة. {LABELS['verification_note']}

## الدروس

| # | الدرس | معرّف المصدر | بصمة مختصرة | إحالات |
|---:|---|---|---|---:|
{chr(10).join(rows)}

كل إحالة في النص على الشكل `〔حN سM sha256=…〕` مع اقتباس حرفي في السطر نفسه؛
`check_lesson.py` يتحقق من البصمة والسطر والاقتباس. أرقام السطور **ليست توقيتات**،
والفحص لا يثبت صحة التفريغ ولا نسبة المتحدث ولا سلامة الاستنتاج.

## الشاشات

لكل درس عشر شاشات تفاعلية مولّدة من نصه بـ`tools/build_lesson_screens.py`،
بنفس هوية «الكراسة والعمود» و` tasees-runtime.js`: توقّع P14، وفرز P02، وبطاقات
الأدوات P17، ودفتر P15. ابدأ من [فهرس الشاشات](02_الشاشات/index.html).

## ملفات Drive غير المستعملة في هذا المسار

{unused_rows}

## قيود موثقة بعد قرار المالك

1. {LABELS['verification_note']} لم تُستمع التسجيلات الأصلية آليًا، ولم تُطابق الطبعة والمتحدث.
2. المراجعة العلمية والسريرية للأوصاف والاقتباسات قيد موثق، خصوصًا [أولويات السلامة](06_أولويات_مراجعة_السلامة.md)
   و[طابور الاقتباسات](05_طابور_مراجعة_الاقتباسات.csv) و[الفرز الأولي](07_فرز_المواضع_بلا_مرشح.md).
3. **لا تشخيص ولا نصيحة علاجية**؛ التمارين عن فهم النص لا عن حالة المتعلم أو غيره،
   ولا تُستعمل أوصاف الاضطرابات على أشخاص.
4. قرار المالك بالاعتماد موثق في [`00_قرارات_المالك.md`](../00_قرارات_المالك.md)؛
   دمج المسارين أو تعديل الخريطة الرسمية أو النشر الخارجي إجراءات منفصلة لم تُنفّذ.

> تغطية الملفات لا تعني قراءة شاملة، وكتابة الدروس لا تعني التحقق المستقل؛
> هذه دروس قابلة للفحص الآلي للسند فقط، معتمدة من المالك بقرار إداري موثق.
'''


def main(argv: list[str]) -> int:
    text = build()
    if '--check' in argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print('✗ فهرس المسار الموازي يحتاج إعادة توليد')
            return 1
        print('ok: فهرس المسار الموازي مطابق للدروس والسجل')
        return 0
    OUT.write_text(text, encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
