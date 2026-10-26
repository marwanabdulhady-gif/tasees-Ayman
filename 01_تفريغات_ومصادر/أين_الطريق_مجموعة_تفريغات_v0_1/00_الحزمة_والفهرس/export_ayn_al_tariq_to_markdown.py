#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export the supplied أين الطريق؟ PDF into traceable Markdown episodes.

The PDF has selectable Arabic text. pypdf's normal extraction mode reconstructs
its RTL text in logical reading order; lines are then minimally whitespace-normalised.
Page markers are retained so readers can return to the original PDF. This is a
transcription export, not a scholarly critical edition: quotations and claims
require checking against the PDF and their primary sources before course use.
"""
from pathlib import Path
from pypdf import PdfReader
import csv, re, shutil, hashlib, unicodedata, zipfile

ROOT = Path(__file__).resolve().parent
PDF = Path('/home/user/uploads/أين الطريق_الطبعة الأولى.pdf')
ORIGINALS = ROOT / 'original_source'
EPISODES = ROOT / 'episodes_markdown'
ORIGINALS.mkdir(parents=True, exist_ok=True)
EPISODES.mkdir(parents=True, exist_ok=True)

# PDF-page positions; the original printed book calls the sequence "steps".
# Episode 00 treats the pre-step preparation as a standalone episode.
EPISODES_SPEC = [
    (0, 'الاستعداد', 9, 53, 'مدخل: طريقٌ بخطوات، وترتيب التعلّم، والتنبيه إلى الفرق بين معرفة الطريق ومكابدته.'),
    (1, 'الخطوة صفر: الجاهلية', 54, 99, 'تشخيص الجاهلية بوصفها أنماطاً وممارسات، لا مرحلة تاريخية منتهية.'),
    (2, 'الخطوة الأولى: التعلّق بشخص النبي ﷺ', 100, 180, 'دور السيرة والقدوة في إخراج الناس من الظلمات إلى النور كما يعرضه المصدر.'),
    (3, 'الخطوة الثانية: اكتساب مؤهلات الخروج من الظلمات إلى النور', 181, 213, 'مؤهلات شخصية، وانتقاء، ومراحل الدعوة السرية في عرض المصدر.'),
    (4, 'الخطوة الثالثة: تحرير العقل وطريقة التفكير', 214, 271, 'منهج التفكير، قراءة الكون، وموانع التفكير الحر في عرض المصدر.'),
    (5, 'الخطوة الرابعة: الارتباط بالله رب العالمين', 272, 305, 'معنى الارتباط بالله، وصلته بتحول الفرد والمجتمع في عرض المصدر.'),
    (6, 'الخطوة الخامسة: الارتباط بالنسك والعبادة', 306, 342, 'مكانة العبادة وإعادة ترتيب الحياة في عرض المصدر.'),
    (7, 'الخطوة السادسة: الارتباط بالدار الآخرة', 343, 376, 'الوجدان والأفق الأخروي كما يقدمه المصدر.'),
    (8, 'الخطوة السابعة: مقاومة الإحباطات وصناعة القوة النفسية', 377, 475, 'الإحباطات والقوة النفسية والقصص والعمل في عرض المصدر.'),
    (9, 'الخطوة الثامنة: إعادة صياغة الروابط والعلاقات', 476, 546, 'الرابطة الإيمانية والعلاقات الاجتماعية وتحدياتها في عرض المصدر.'),
    (10, 'الخطوة التاسعة: إنشاء لهفة التلقي والتعلم', 547, 583, 'التعلم، تلقي العلم، والصبر على الطلب في عرض المصدر.'),
    (11, 'الخطوة العاشرة: القرآن كمصدر وحيد للتلقي', 584, 618, 'مركزية القرآن في التلقي كما يطرحها المصدر.'),
    (12, 'الخطوة الحادية عشرة: تزكية النفوس', 619, 715, 'التزكية والتربية والصحبة ووظيفة المربي في عرض المصدر.'),
    (13, 'الخطوة الثانية عشرة: فهم حقائق الإسلام الكبرى', 716, 767, 'الفرد والرسالة والشمولية والعمل في عرض المصدر.'),
    (14, 'الخطوة الثالثة عشرة: فريضة العمل لدين الله', 768, 813, 'العمل للدين في عرض المصدر؛ تشمل خاتمة المصدر في PDF 812–813.'),
]

def normalise_logical_line(line: str) -> str:
    """Minimally normalize a logically ordered Arabic extraction line."""
    line = unicodedata.normalize('NFKC', line).replace('\u200f', '').replace('\u200e', '')
    line = re.sub(r'\s+', ' ', line).strip()
    # Remove isolated private-use/icon glyphs left by the source PDF, but retain
    # Arabic, Quranic, Latin, digits, and punctuation.
    line = ''.join(ch for ch in line if not (0xE000 <= ord(ch) <= 0xF8FF))
    return line

def page_to_markdown(page, pdf_page: int) -> str:
    # Normal pypdf extraction preserves the source's RTL reading order more
    # reliably than layout mode for this Word-generated PDF.
    raw = page.extract_text() or ''
    lines = [normalise_logical_line(line) for line in raw.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return f'<!-- صفحة PDF {pdf_page}: لا نص قابل للاستخراج؛ راجع النسخة الأصلية. -->\n'
    # A hard page marker protects traceability while letting Markdown render in
    # reading order. Lines remain separate because the PDF layout often contains
    # meaningful Quran/hadith/table breaks.
    return f'\n<!-- بداية صفحة PDF {pdf_page} -->\n\n' + '\n\n'.join(lines) + f'\n\n<!-- نهاية صفحة PDF {pdf_page} -->\n'

def safe_filename(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', '', s)
    s = re.sub(r'\s+', '_', s).strip('_')
    return s[:120]

reader = PdfReader(str(PDF))
assert len(reader.pages) == 820, f'Expected 820 PDF pages; found {len(reader.pages)}'

shutil.copy2(PDF, ORIGINALS / PDF.name)
records = []
for num, title, start, end, scope in EPISODES_SPEC:
    # Page numbers in the manifest are human/PDF numbers, not zero-based indexes.
    assert 1 <= start <= end <= len(reader.pages)
    filename = f'{num:02d}-{safe_filename(title)}.md'
    out = EPISODES / filename
    frontmatter = [
        '---',
        f'episode: {num}',
        f'title: "{title}"',
        'series: "أين الطريق؟"',
        'source_type: "PDF supplied by user; first edition"',
        f'pdf_pages: "{start}-{end}"',
        'language: ar',
        'extraction_method: "pypdf RTL text extraction; whitespace minimally normalized"',
        'verification_status: "transcription export — verify quotations, citations, and claims against PDF / primary sources before course use"',
        '---', '',
        f'# الحلقة {num:02d}: {title}', '',
        f'> **النطاق:** {scope}', '',
        f'> **التتبع:** الصفحات {start}–{end} من ملف PDF المرفق `أين الطريق_الطبعة الأولى.pdf`.', '',
        '> **تنبيه تحريري:** هذا تصدير نصي آلي من PDF عربي ذي تخطيط بصري. حُفظت علامات الصفحات، لكن قد تظهر أخطاء فصل أو محاذاة أو ترميز؛ لا يُستخدم النص وحده للتحقق من اقتباس أو دعوى أو إسناد.', '',
        '## النص المستخرج', ''
    ]
    text = '\n'.join(frontmatter)
    for p in range(start, end + 1):
        text += page_to_markdown(reader.pages[p - 1], p)
    # Preserve conclusion provenance explicitly inside the final episode.
    if num == 14:
        text += '\n## ملاحظة عن الخاتمة\n\nتضم هذه الحلقة خاتمة المصدر الواقعة في صفحات PDF 812–813؛ أمّا الفهرس في الصفحات 814–820 فلا يدخل في التصدير الحلقي.\n'
    out.write_text(text, encoding='utf-8')
    records.append({
        'episode': num, 'title': title, 'pdf_start_page': start,
        'pdf_end_page': end, 'pdf_page_count': end-start+1,
        'filename': filename, 'scope_note': scope,
        'verification_status': 'transcription export; verify against supplied PDF / primary sources before course use'
    })

with (ROOT / 'source_map.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=records[0].keys())
    writer.writeheader(); writer.writerows(records)

readme = f'''# أين الطريق؟ — مجموعة Markdown قابلة للتتبع

- **المصدر:** `{PDF.name}`، ملف PDF مرفق من المستخدم، طبعة أولى.
- **عدد صفحات PDF:** {len(reader.pages)}.
- **بنية التصدير:** 15 ملف Markdown: تمهيد «الاستعداد»، ثم الخطوة صفر، فالخطوات 1–13.
- **علامات التتبع:** يحمل كل ملف نطاق صفحات PDF، وتحمل كل صفحة داخل الملف تعليق Markdown ببدايتها ونهايتها.

## حدود الاستخدام

هذا التصدير يسهل البحث والربط بالمقرر، ولا يحول المادة إلى مصدر محكّم أو إلى تزكية تلقائية لكل دعوى فيها. أُخرج النص من PDF عربي ذي تخطيط معقّد، وحُفظت علامات الصفحات وأزيلت المسافات الزائدة فقط. لذلك يلزم الرجوع إلى PDF المرفق للتحقق من الاقتباسات، وضبط السياق، والاستدلالات، وأي إحالات علمية/تاريخية/فقهية قبل إدراجها في مواد الدورة.

## الملفات

- `episodes_markdown/` — الحلقات/الخطوات الخمس عشرة.
- `source_map.csv` — مطابقة الحلقة بالعنوان والصفحات والنطاق.
- `original_source/` — نسخة المصدر الأصلي كما وردت من المستخدم.
- `export_ayn_al_tariq_to_markdown.py` — مولّد التصدير القابل لإعادة التشغيل.
'''
(ROOT / 'README.md').write_text(readme, encoding='utf-8')

zip_path = ROOT / 'ayn_al_tariq_markdown_collection.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(ROOT/'README.md', 'README.md')
    z.write(ROOT/'source_map.csv', 'source_map.csv')
    z.write(ROOT/'export_ayn_al_tariq_to_markdown.py', 'export_ayn_al_tariq_to_markdown.py')
    for f in sorted(EPISODES.glob('*.md')):
        z.write(f, f'episodes_markdown/{f.name}')
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == 18, len(z.namelist())

md5 = hashlib.md5(zip_path.read_bytes()).hexdigest()
print(f'Exported {len(records)} episode Markdown files')
print(f'Coverage: PDF pages {min(r["pdf_start_page"] for r in records)}–{max(r["pdf_end_page"] for r in records)} (content only; cover/front matter/TOC excluded)')
print(f'ZIP: {zip_path.name}; entries: {len(zipfile.ZipFile(zip_path).namelist())}; MD5: {md5}')
