#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يولّد دروس القالب التكميلية من `course_lesson_data.py` ويتحقق من سندها.

    python3 08_دورات_القوائم/tools/build_course_lessons.py           # كتابة
    python3 08_دورات_القوائم/tools/build_course_lessons.py --check    # مقارنة بلا كتابة

الاقتباسات تُستخرج حرفيًا من أول N كلمة في السطر المحدد من ملف Drive، ثم
يُتحقق من وجودها داخل نطاق السطر ومن بصمة SHA-256 لبايتات الملف، قبل كتابة
أي درس. الفحص المستقل `check_lesson.py` يعيد التحقق من الدرس الناتج.

هذه نصوص معتمدة من المالك للنشر داخل المستودع، مع قيود موثقة: الفحص يثبت موضع
الاقتباس لا صحة التفريغ ولا نسبة المتحدث ولا سلامة الاستنتاج ولا مطابقة التسجيل،
ولا يُثبت الاعتماد آليًا.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from course_lesson_data import COURSES  # noqa: E402
from owner_decisions import LABELS, SHORT_STATUS, status  # noqa: E402

PKG = HERE.parent
ROOT = PKG.parent
IMPORT = ROOT / 'transcripts' / 'drive-import-2026-11-01'
INVENTORY = ROOT / '09_تفريغات_أيمن' / 'drive_inventory.json'
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

DRAFT_NOTE = (LABELS['draft_note'] + ' هذه إعادة صياغة تعليمية؛ الاقتباسات حرفية من التفريغ '
              'لا من تسجيل تم الاستماع إليه. أرقام السطور ليست توقيتات. ' + LABELS['publication_note'])

METHOD_NOTE = ('هذه قراءة مقاطع محددة من ملف واحد؛ لا يُعدّل الملف الأصلي، ولا تُدمج النسخ، ولا '
               'تُحوّل الإحالة إلى توقيت. الفحص الآلي يثبت موضع الاقتباس وبصمة البايتات فقط، ولا '
               'يثبت نسبة المتحدث ولا صحة المعنى ولا سلامة الاستنتاج. ' + LABELS['verification_note'])

EXTRA_NOTES = {
    'psy': ('النسخة الأساسية في `الدروس/` والمسودة القصيرة في `مسودات_الدروس/` محفوظتان دون '
            'تعديل؛ هذا مسار موازٍ معتمد من المالك لا يستبدلهما، ولا تُنقل إليه توقيتات التفريغ القديم.'),
    'l2': ('ملفا المستوى الثاني السادس والسابع يُقرآن منفصلين؛ التشابه اللفظي لا يثبت تطابق '
           'التسجيلين، والفصل قرار مراجعة حتى يُحسم بالتسجيلات.'),
}

BLOCK_LABELS = ['الكتلة ١', 'الكتلة ٢', 'الكتلة ٣']


def norm(s: str) -> str:
    """مطابقة تطبيع `check_lesson.py` للتأكد من أن الاقتباس سيُوجد في المتن."""
    s = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', s)
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'), ('ى', 'ي'),
                 ('ة', 'ه'), ('ؤ', 'و'), ('ئ', 'ي')):
        s = s.replace(a, b)
    s = re.sub(r'[«»"\'،؛:.,!؟?()\[\]{}<>ـ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def source_files(folder: str) -> dict[int, Path]:
    d = IMPORT / folder
    out = {}
    for f in sorted(d.glob('*.txt')):
        m = re.match(r'^(\d+)', f.name)
        if m:
            n = int(m.group(1))
            if n in out:
                raise ValueError(f'duplicate episode number in {folder}: {f.name}')
            out[n] = f
    if not out:
        raise ValueError(f'no text sources in {d}')
    return out


def phrase(line: str, nwords: int) -> str:
    """أول nwords كلمة كما هي حرفيًا في السطر (تحفظ المسافات الأصلية)."""
    words = list(re.finditer(r'\S+', line))
    if len(words) < nwords:
        raise ValueError(f'line has {len(words)} words, need {nwords}: {line[:60]!r}')
    return line[words[0].start():words[nwords - 1].end()]


def build_lesson(course: dict, spec: dict, files: dict[int, Path], inventory: dict[str, dict]) -> str:
    n = spec['n']
    src = files[n]
    rel = str(src.relative_to(ROOT))
    entry = inventory[rel]
    data = src.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != entry['sha256']:
        raise ValueError(f'{rel}: SHA-256 mismatch with Drive inventory')
    lines = data.decode('utf-8').splitlines()
    link = quote(Path(os.path.relpath(src, PKG / course['folder'] / '01_نصوص_الدروس')).as_posix(), safe='/')

    out = [f'# الدرس {str(n).translate(AR)} — {spec["title"]}', '', DRAFT_NOTE, '',
           '## افتتاح وخطاف', '', spec['hook'], '',
           '## سؤال الدرس', spec['question'], '',
           '## مصدر الدرس',
           f'[التفريغ النصي للحلقة {n}]({link}) · معرّف المصدر `{entry["id"]}` · SHA-256 `{sha}`.',
           'تعرض الاقتباسات كما هي في الملف، بما فيها أخطاء التفريغ؛ والإحالة تثبت مكان النص '
           'لا صحته التاريخية أو العلمية.']
    if course['key'] in EXTRA_NOTES:
        out.append(EXTRA_NOTES[course['key']])
    out += ['', METHOD_NOTE, '',
            f'**ما أخذناه:** {spec["taken"]} **ما أجّلناه:** {spec["deferred"]} '
            'هذه القراءة لمقاطع محددة، وليست تفريغًا كاملًا ولا بديلًا عن المحاضرة.', '']

    quote_count = 0
    whole_norm = norm(data.decode('utf-8'))
    for label, b in zip(BLOCK_LABELS, spec['blocks']):
        out += [f'## {label} — {b["heading"]}', '', b['intro'], '']
        for line_no, nwords, lead, comment in b['quotes']:
            if not 1 <= line_no <= len(lines):
                raise ValueError(f'{course["key"]}/{n}: line {line_no} out of range')
            q = phrase(lines[line_no - 1], nwords)
            if not 3 <= len(q.split()) <= 30 or '«' in q or '»' in q or '〔' in q:
                raise ValueError(f'{course["key"]}/{n}: invalid quote at L{line_no}: {q!r}')
            if q not in ''.join(lines[line_no - 1:line_no]) or norm(q) not in whole_norm:
                raise ValueError(f'{course["key"]}/{n}: quote not literal at L{line_no}: {q!r}')
            out += [f'{lead}«{q}» 〔ح{n} س{line_no} sha256={sha}〕', comment]
            quote_count += 1
        out += ['', b['discussion'],
                f'ودي أداة {b["tool_name"]} تُعاد في الدرس التالي: الاقتباس يثبت الموضع، '
                'والمرجع يثبت المعنى، والتسجيل يثبت النسبة؛ ولا يقوم واحد منها مقام الآخر.', '',
                f'**أداة الكتلة: {b["tool_name"]}.** {b["tool_text"]}', '']

    out += ['## مصيدة الفهم',
            spec['trap'] + ' الفحص الآلي لا يحسم هذا؛ يُسجّل في طابور الاعتماد مع قيوده.', '',
            '## المهمة', '',
            f'**مستكشف:** {spec["tasks"][0]}', '',
            f'**ممارس:** {spec["tasks"][1]}', '',
            f'**متقدم:** {spec["tasks"][2]}', '',
            'المهمة عن فهم النص لا عن تقويم أشخاص أو حالات؛ ولا يُطلب فيها رأي سريري ولا حكم '
            'تاريخي، وما لم تجد له شاهدًا يُترك في طابور الاعتماد.', '',
            '### نموذج للمراجعة الذاتية',
            spec['review'] + ' إن ظهرت خانة بلا شاهد، تُترك بعبارة لا أعلم بعد بدل ملئها بحدس.', '',
            '## القفلة', spec['closing'],
            'قرار المالك بالاعتماد موثق، لكنه لا يثبت التسجيل أو المراجع؛ والخرائط الرسمية لم تُعدّل.', '',
            f'الدرس الجاي {spec["next"]} استنى هناك.']
    text = '\n'.join(out) + '\n'
    if text.count('«') != quote_count or quote_count < 6:
        raise ValueError(f'{course["key"]}/{n}: unexpected guillemet/citation count {quote_count}')
    body = re.sub(r'〔[^〕]*〕', ' ', text)
    body = re.sub(r'\]\([^)]*\)', ']', body)
    body = re.sub(r'`[^`]*`', ' ', body)
    words = len(body.split())
    if not 700 <= words <= 1200:
        raise ValueError(f'{course["key"]}/{n}: {words} words (need 700–1200)')
    return text


def build() -> dict[Path, str]:
    docs = json.loads(INVENTORY.read_text(encoding='utf-8'))['documents']
    inventory = {d['path']: d for d in docs}
    out = {}
    for course in COURSES:
        files = source_files(course['drive_folder'])
        for spec in course['lessons']:
            path = PKG / course['folder'] / '01_نصوص_الدروس' / f'lesson-{spec["n"]:02d}.md'
            out[path] = build_lesson(course, spec, files, inventory)
    return out


def main(argv: list[str]) -> int:
    generated = build()
    check = '--check' in argv
    changed = [str(p.relative_to(ROOT)) for p, text in generated.items()
               if not p.exists() or p.read_text(encoding='utf-8') != text]
    if check:
        if changed:
            print('✗ دروس تحتاج إعادة توليد:')
            for c in changed:
                print('  ' + c)
            return 1
        print(f'ok: {len(generated)} درسًا مولَّدًا مطابق للملفات')
        return 0
    for p, text in generated.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} lessons')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
