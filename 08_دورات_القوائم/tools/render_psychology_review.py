#!/usr/bin/env python3
"""Render the manual queue classification, refusing stale inputs."""
import csv
import hashlib
import html
import json
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
COURSE = ROOT / '08_دورات_القوائم/علم_النفس'
QUEUE = COURSE / '05_طابور_مراجعة_الاقتباسات.csv'
REVIEW = COURSE / '07_تصنيف_أولي_للمواضع_بلا_مرشح.json'
OUT = COURSE / '07_فرز_المواضع_بلا_مرشح.md'
CATEGORIES = {
    'activity': ('سؤال أو نشاط أو مثال تعليمي', 'ميّز تأليف الدرس من النقل؛ راجع الافتراضات العلمية في السؤال أو المثال عند الحاجة.'),
    'term': ('مصطلح أو تسمية', 'لا تُعامل التسمية كاقتباس آليًا؛ راجع معناها وصحة سياقها.'),
    'quote': ('نقل أو اختصار محتمل', 'قارن السياق واللفظ بالمصدر والتسجيل؛ أزل علامات الاقتباس إذا كانت إعادة صياغة.'),
    'reference': ('مرجع أو رقم أو نسبة', 'تحقق من المرجع الأصلي والرقم والسياق، ثم افصل التوثيق عن كلام المحاضرة.'),
    'scientific': ('ادعاء علمي أو تاريخي', 'افحص نسبته ومصادر مستقلة ومراجعة اختصاصية عند اللزوم؛ لا يُعتمد من التفريغ وحده.'),
    'clinical': ('سياق نفسي أو سريري حساس', 'مراجعة مختص وأدلة حديثة وصياغة غير تشخيصية؛ تحقّق من النقل والتسجيل أيضًا.'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cell(text):
    return html.escape(str(text), quote=False).replace('|', '&#124;').replace('\n', ' ')


def build():
    review = json.loads(REVIEW.read_text(encoding='utf-8'))
    if sha(QUEUE.read_bytes()) != review['queue_sha256']:
        raise ValueError('Queue changed; manual review must be revisited before rendering')
    with QUEUE.open(encoding='utf-8', newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['legacy_count'] == '0' and r['drive_count'] == '0']
    items = review['items']
    expected = [(r['lesson'], int(r['line']), r['quoted_text'], r['lesson_sha256']) for r in rows]
    actual = [(i['lesson'], i['line'], i['quoted_text'], i['lesson_sha256']) for i in items]
    if expected != actual:
        raise ValueError('Manual review does not cover the exact unmatched queue rows in order')
    counts = Counter()
    for i in items:
        if i['category'] not in CATEGORIES:
            raise ValueError('Unknown review category')
        lesson = i['lesson']
        if Path(lesson).name != lesson or not lesson.endswith('.md'):
            raise ValueError('Invalid lesson filename')
        data = (COURSE / 'الدروس' / lesson).read_bytes()
        if sha(data) != i['lesson_sha256']:
            raise ValueError(f'Lesson changed: {lesson}')
        lines = data.decode('utf-8').splitlines()
        if i['line'] < 1 or i['line'] > len(lines) or '«' + i['quoted_text'] + '»' not in lines[i['line']-1]:
            raise ValueError(f'Quote no longer present: {lesson}:{i["line"]}')
        counts[i['category']] += 1
    out = ['# فرز أولي للمواضع التي لم يظهر لها مرشح آلي', '',
           '> تقرير مولّد من التصنيف اليدوي في `07_تصنيف_أولي_للمواضع_بلا_مرشح.json`، باستخدام `tools/render_psychology_review.py`. تغيّر الطابور أو أحد ملفات الدروس يستوجب إعادة المراجعة قبل التوليد.', '',
           f'فُرزت {len(items)} واقعة في الدروس العشرة بحسب سياق النص، **لا بحسب صحة المحتوى أو نسبته**. عدم ظهور مرشح قد ينتج عن اختلاف الصياغة أو محدودية البحث. لم يُستمع إلى التسجيلات، ولم تُراجع الأدلة الخارجية أو المختصون. هذا الفرز لا يحسم الـ51 واقعة الأخرى ذات المرشحات، ولا يغطي الادعاءات غير المحاطة بعلامات اقتباس.', '',
           f'بصمة الطابور: `{review["queue_sha256"]}`. بصمة كل درس مثبتة في ملف التصنيف الآلي القراءة.', '',
           '## مفتاح الفرز والإجراء المقترح', '', '| التصنيف الأولي | العدد | الخطوة التالية |', '|---|---:|---|']
    for key,(name,action) in CATEGORIES.items():
        out.append(f'| {name} | {counts[key]} | {action} |')
    out += ['', 'التصنيف واحد لكل واقعة لأولوية العمل فقط، وقد تتداخل الحاجة إلى تحقق لغوي أو علمي أو سريري. اقرأ سطر الدرس وسياقه كاملاً؛ علامات الحذف قد تدل على اختصار لا اقتباس حرفي.', '',
            '## جميع الواقعات المشمولة', '', '| الدرس والموضع | النص كما في الدرس | التصنيف الأولي |', '|---|---|---|']
    for i in items:
        link = quote('الدروس/' + i['lesson'], safe='/') + '#L' + str(i['line'])
        out.append(f"| [{cell(i['lesson'][:2])}: س{i['line']}]({link}) | «{cell(i['quoted_text'])}» | {CATEGORIES[i['category']][0]} |")
    out += ['', '## إعادة التوليد', '',
            'بعد تعديل الدروس أو المصادر، أعد بناء سجل علم النفس ثم طابور الاقتباسات وفق منهجه، وراجع فروقه يدويًا وأعد تصنيف الواقعات في ملف JSON مع تحديث بصمة الطابور وبصمات الدروس. بعد ذلك نفّذ من جذر المستودع: `python3 08_دورات_القوائم/tools/render_psychology_review.py`. الفاحص يرفض اختلاف الطابور أو نصوص الدروس عن التصنيف؛ لا يكشف تغيّر المصادر إذا لم يُعَد بناء الطابور أولًا.', '',
            'راجع كذلك [أولويات السلامة](06_أولويات_مراجعة_السلامة.md) و[منهج الطابور](05_منهج_طابور_الاقتباسات.md). لم يتغير نص أي درس بهذا الفرز.', '']
    return '\n'.join(out)


def main():
    OUT.write_text(build(), encoding='utf-8')
    print(f'Wrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
