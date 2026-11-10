#!/usr/bin/env python3
"""Create a repeatable *candidate* quote-review queue; never edit course text."""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ROOT = PKG.parent
sys.path.insert(0, str(PKG / 'tools'))
from check_lesson import CITE, CITE_G, CITE_L, CITE_P, QUOTE, norm  # noqa: E402

COURSE = PKG / 'علم_النفس'
CATALOG = ROOT / 'ayman_rag/psychology_inventory.json'
CSV = COURSE / '05_طابور_مراجعة_الاقتباسات.csv'
REPORT = COURSE / '05_منهج_طابور_الاقتباسات.md'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hint(line):
    s = line.strip()
    if re.match(r'^[-*]\s*\[[ xX]\]', s):
        return 'قائمة تحقق — فحص بشري'
    if s.startswith('|'):
        return 'جدول — فحص بشري'
    if s.startswith('#'):
        return 'عنوان — فحص بشري'
    return 'نص — فحص بشري'


def csv_safe(value):
    # A quote is untrusted text: avoid spreadsheet formula execution. The
    # original lesson remains the source of truth for any escaped cell.
    if isinstance(value, str) and (value.startswith(('\t', '\r', '\n')) or re.match(r'^\s*[=+\-@]', value)):
        return "'" + value
    return value


def find_line(lines, phrase):
    # Inspect the same line or up to two following lines; a source location is
    # a candidate for context review, never proof of an intentional quotation.
    for i in range(len(lines)):
        if phrase in lines[i]:
            return i + 1, i + 1
    for i in range(len(lines)):
        for size in (2, 3):
            if i + size <= len(lines) and phrase in ' '.join(lines[i:i + size]):
                return i + 1, i + size
    return None


def build():
    catalog_bytes = CATALOG.read_bytes()
    docs = json.loads(catalog_bytes)['documents']
    if len(docs) != 21:
        raise ValueError('expected 21 psychology sources')
    sources = []
    for doc in docs:
        p = (ROOT / doc['path']).resolve()
        allowed = [(ROOT / 'transcripts/03-psychology').resolve(), (ROOT / 'transcripts/drive-import-2026-11-01').resolve()]
        if not any(p.is_relative_to(a) for a in allowed) or not p.is_file() or digest(p) != doc['sha256']:
            raise ValueError(f"unsafe, missing, or changed source: {doc['path']}")
        sources.append((doc, [norm(line) for line in p.read_text(encoding='utf-8').splitlines()]))
    lessons = sorted((COURSE / 'الدروس').glob('[0-9][0-9]_*.md'))
    if len(lessons) != 10:
        raise ValueError('expected 10 baseline lessons; review course contents')
    rows = []
    for lesson in lessons:
        for line_no, line in enumerate(lesson.read_text(encoding='utf-8').splitlines(), 1):
            for q in QUOTE.findall(line):
                phrase = norm(q)
                if len(phrase) < 4:
                    continue
                matches = {'legacy': [], 'drive': []}
                for doc, lines in sources:
                    hit = find_line(lines, phrase)
                    if hit:
                        kind = 'drive' if doc['id'].startswith('drive-') else 'legacy'
                        a, b = hit
                        matches[kind].append(f"{doc['id']}:{a}" + (f'-{b}' if a != b else ''))
                rows.append({'lesson': lesson.name, 'lesson_sha256': digest(lesson), 'line': line_no,
                             'quoted_text': q, 'context_hint': hint(line),
                             'formal_refs_on_line': ' '.join(m.group(0) for pattern in (CITE, CITE_P, CITE_G, CITE_L) for m in pattern.finditer(line)),
                             'legacy_count': len(matches['legacy']), 'legacy_candidates': '; '.join(matches['legacy']),
                             'drive_count': len(matches['drive']), 'drive_candidates': '; '.join(matches['drive'])})
    return rows, lessons, docs, hashlib.sha256(catalog_bytes).hexdigest()


def main():
    rows, lessons, docs, catalog_sha = build()
    fields = ['lesson', 'lesson_sha256', 'line', 'quoted_text', 'context_hint', 'formal_refs_on_line', 'legacy_count', 'legacy_candidates', 'drive_count', 'drive_candidates']
    with CSV.open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows({k: csv_safe(v) for k, v in row.items()} for row in rows)
    lines = ['# طابور مراجعة اقتباسات علم النفس — فرز آلي', '',
             '> **ملف مولَّد** بواسطة `tools/build_psychology_quote_triage.py`؛ لا يُعدل يدويًا. مصدر التفاصيل [`05_طابور_مراجعة_الاقتباسات.csv`](05_طابور_مراجعة_الاقتباسات.csv).', '',
             'هذا جرد آلي للعبارات بين «…» بطول 4–300 حرف في سطر واحد من الدروس العشرة، لا حكم على صحة الدرس أو نسبة المتحدث. علامات التنصيص قد تشير إلى سؤال، مصطلح أو مثال تدريبي لا اقتباسًا من المحاضرة. التلميح السياقي تقريبي ولا يغني عن الفرز البشري. تسجل خانة الإحالات الرسمية ما يظهر على السطر فقط؛ وجود أو غياب رابط في موضع آخر لا يُحسم بها. تحمي CSV أي خلية تبدأ بصيغة جدول بإضافة فاصلة عليا؛ أصل النص في الدرس.', '',
             'تُبحث العبارة بعد تطبيع فاحص الدروس (الهمزات والتشكيل وعلامات الترقيم والمسافات) داخل سطر مصدر أو حتى ثلاثة سطور متجاورة؛ النتيجة **مرشح** وليست نقلًا حرفيًا مؤكدًا، وقد يكون التطابق شائعًا أو خارج السياق. إذا تكرر التعبير داخل مصدر يُعرض أول موضع فقط. عدم ظهور مرشح لا يثبت الخطأ، خصوصًا عند اختلاف التفريغ أو امتداد العبارة أكثر من ثلاثة سطور.', '',
             'تُعرض المصادر بمعرّفات وسطور النص من سجل علم النفس، وليس بدقائق التسجيل. يحفظ السجل النسخ الـ11 المستوردة والـ10 القديمة منفصلة؛ معرّفات Drive لا تحمل طوابع. المصادر والتسجيل والمتحدث ودقة التفريغ غير متحققة. لا يُستخدم الطابور لتشخيص نفسي أو لتأكيد ادعاء علمي.', '',
             f'- بصمة سجل المصادر: `{catalog_sha}`',
             f'- الملفات: {len(lessons)} دروس و{len(docs)} مصدرًا؛ المواضع المؤهلة: {len(rows)}.', '',
             '| الدرس | مواضع علامات التنصيص | مرشح قديم واحد على الأقل | مرشح Drive واحد على الأقل | بلا مرشح في أي النسختين |',
             '|---|---:|---:|---:|---:|']
    for lesson in lessons:
        subset = [r for r in rows if r['lesson'] == lesson.name]
        lines.append(f"| [{lesson.name}](الدروس/{lesson.name}) | {len(subset)} | {sum(bool(r['legacy_count']) for r in subset)} | {sum(bool(r['drive_count']) for r in subset)} | {sum(not r['legacy_count'] and not r['drive_count'] for r in subset)} |")
    lines += ['', '## آلية المراجعة', '',
              '1. راجع استعمال العلامتين في الدرس أولًا: هل هو مصطلح أو سؤال أو مثال، أم نقل يُنسب للمحاضرة؟',
              '2. افتح مواضع المرشحين في المصدرين عبر معرّف المصدر في `ayman_rag/psychology_inventory.json`، وافحص السياق؛ لا تدمج النسخ أو تنقل توقيت إحداها تلقائيًا.',
              '3. للعبارات المنسوبة، قارن بالتسجيل الأصلي عند توفره، ثم بمراجع علمية مستقلة عند الحاجة؛ عدّل مسودة الدرس فقط بعد المراجعة وفق مسار اعتماد المشروع.',
              '4. بعد أي تغيير في الدروس أو المصادر، أعد بناء سجل علم النفس ثم هذا الطابور. تحقّق من الفروق لأن بصمات النسخ القديمة تصف البايتات الحالية لا مصدرًا خارجيًا مستقلًا.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {len(rows)} quote candidates from {len(lessons)} lessons; no course or source text changed.')
    print('no match in either:', sum(not r['legacy_count'] and not r['drive_count'] for r in rows))


if __name__ == '__main__':
    main()
