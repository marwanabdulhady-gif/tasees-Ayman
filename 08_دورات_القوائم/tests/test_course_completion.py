# -*- coding: utf-8 -*-
"""فحوص اكتمال المسودات المولّدة: نصوص، وشاشات، وخرائط، وفهارس.

الاختبارات تثبت التطابق البنيوي والسند الآلي فقط؛ لا تُثبت صحة التفريغ ولا
اعتماد المحتوى ولا مطابقة التسجيلات.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / '08_دورات_القوائم'
TOOLS = PKG / 'tools'
COURSES = [
    ('التأسيس_المعرفي/المستوى_الأول', 'cognitive-foundation-1', 8),
    ('التأسيس_المعرفي/المستوى_الثاني', 'cognitive-foundation-2', 7),
    ('علم_النفس', None, 10),
]


def run(script, *args):
    return subprocess.run([sys.executable, str(TOOLS / script), *args], cwd=ROOT,
                          capture_output=True, text=True)


class CourseCompletionTests(unittest.TestCase):
    def test_generated_files_are_reproducible(self):
        for script in ('build_course_lessons.py', 'build_lesson_screens.py',
                       'build_parallel_track_index.py',
                       'build_playlist_course_drafts.py', 'build_playlist_course_screens.py'):
            with self.subTest(script=script):
                r = run(script, '--check')
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_lesson_has_ten_screens_with_matching_source(self):
        for folder, _, count in COURSES:
            course = PKG / folder
            lessons = sorted((course / '01_نصوص_الدروس').glob('lesson-[0-9][0-9].md'))
            screens = sorted((course / '02_الشاشات').glob('lesson-[0-9][0-9].html'))
            self.assertEqual((len(lessons), len(screens)), (count, count), folder)
            for lesson in lessons:
                with self.subTest(lesson=str(lesson)):
                    n = int(lesson.stem[-2:])
                    text = lesson.read_text(encoding='utf-8')
                    sha = re.search(r'SHA-256\s+`([0-9a-f]{64})`', text).group(1)
                    page = course / '02_الشاشات' / f'lesson-{n:02d}.html'
                    html = page.read_text(encoding='utf-8')
                    data = json.loads(re.search(
                        r'<script type="application/json" id="week">\n(.*?)\n</script>',
                        html, re.S).group(1))
                    self.assertEqual(data['source_sha'], sha)
                    self.assertEqual(data['lesson'], n)
                    self.assertEqual(len(data['screens']), 10)
                    self.assertEqual(data['screens'][0]['layout'], 'L1')
                    self.assertEqual(data['screens'][-1]['layout'], 'L7')
                    self.assertIn('غير معتمدة', data['draft'])
                    patterns = [s.get('pattern') for s in data['screens'] if s.get('pattern')]
                    self.assertTrue({'P14', 'P02', 'P17', 'P15'} <= set(patterns))
                    self.assertEqual(set(data['screens'][-1]['task']),
                                     {'مستكشف', 'ممارس', 'متقدم'})
                    # كل شاشة تشير إلى سند، وكل رابط/أصل محلي موجود.
                    self.assertTrue(all(s.get('sanad') for s in data['screens']))
                    href = page.parent / data['text_href']
                    self.assertTrue(href.exists())
                    for rel in re.findall(r'<(?:link|script)[^>]*?(?:href|src)="([^"]+)"', html):
                        if rel.startswith('http') or rel.startswith('#'):
                            continue
                        target = (page.parent / rel.split('#')[0]).resolve()
                        self.assertTrue(target.exists(), f'{page.name}: {rel}')

    @unittest.skipUnless(shutil.which('node'), 'node is not installed')
    def test_inline_scripts_parse(self):
        screens = sorted((PKG / 'علم_النفس' / '02_الشاشات').glob('lesson-*.html'))
        self.assertEqual(len(screens), 10)
        with tempfile.TemporaryDirectory() as tmp:
            for page in screens:
                html = page.read_text(encoding='utf-8')
                scripts = re.findall(
                    r'<script(?![^>]*type="application/json")(?![^>]*src)[^>]*>(.*?)</script>',
                    html, re.S)
                self.assertEqual(len(scripts), 1, page.name)
                js = Path(tmp) / (page.stem + '.js')
                js.write_text(scripts[0], encoding='utf-8')
                r = subprocess.run(['node', '--check', str(js)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, page.name + ': ' + r.stderr)

    def test_indexes_link_every_lesson(self):
        hub = (PKG / 'index.html').read_text(encoding='utf-8')
        for folder, _, count in COURSES:
            course = PKG / folder
            idx = course / '02_الشاشات' / 'index.html'
            self.assertTrue(idx.exists())
            self.assertIn(f'{folder}/02_الشاشات/index.html', hub)
            content = idx.read_text(encoding='utf-8')
            for n in range(1, count + 1):
                with self.subTest(index=idx.name, n=n):
                    self.assertIn(f'lesson-{n:02d}.html', content)
                    self.assertIn(f'../01_نصوص_الدروس/lesson-{n:02d}.md', content)

    def test_foundation_maps_link_texts_and_screens(self):
        for folder, slug, count in COURSES[:2]:
            with self.subTest(slug=slug):
                course = PKG / folder
                cmap = json.loads((course / '00_خريطة_الدورة.json').read_text(encoding='utf-8'))
                self.assertEqual(cmap['status'], 'خريطة')
                self.assertEqual(len(cmap['lessons']), count)
                for lesson in cmap['lessons']:
                    n = lesson['n']
                    self.assertEqual(lesson['text'], f'01_نصوص_الدروس/lesson-{n:02d}.md')
                    self.assertEqual(lesson['page'], f'02_الشاشات/lesson-{n:02d}.html')
                    self.assertEqual(lesson['text_status'], 'مسودة غير معتمدة')
                    self.assertTrue((course / lesson['text']).exists())
                    self.assertTrue((course / lesson['page']).exists())
                r = subprocess.run([sys.executable, str(TOOLS / 'check_playlist_course.py'), slug],
                                   cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_parallel_track_index_matches_inventory_and_keeps_editions_separate(self):
        course = PKG / 'علم_النفس'
        cmap = json.loads((course / '00_خريطة_الدورة.json').read_text(encoding='utf-8'))
        self.assertEqual(cmap['status'], 'نصوص بلا خريطة')
        self.assertEqual(cmap['lessons'], [])
        index = (course / '01_فهرس_المسودة_الموازية.md').read_text(encoding='utf-8')
        docs = json.loads((ROOT / '09_تفريغات_أيمن/drive_inventory.json').read_text(
            encoding='utf-8'))['documents']
        psych = {int(re.match(r'^(\d+)', Path(d['path']).name).group(1)): d
                 for d in docs if 'دورة-علم-النفس-' in d['path']}
        self.assertEqual(len(psych), 11)
        for n in range(1, 11):
            with self.subTest(n=n):
                self.assertIn(f'01_نصوص_الدروس/lesson-{n:02d}.md', index)
                self.assertIn(psych[n]['id'], index)
                self.assertIn(psych[n]['sha256'][:12], index)
                src = ROOT / psych[n]['path']
                self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), psych[n]['sha256'])
        self.assertIn(psych[11]['id'], index)
        self.assertIn('لم يُكتب له درس', index)
        self.assertIn('لا تشخيص ولا نصيحة علاجية', index)
        self.assertIn('نصوص بلا خريطة', index)

    def test_checker_zero_notes_and_lesson_prose_is_clean(self):
        cases = [
            ('التأسيس_المعرفي/المستوى_الأول/01_نصوص_الدروس',
             'transcripts/drive-import-2026-11-01/دورة-التأسيس-المعرفى-1-م-أيمن-عبدالرحيم'),
            ('التأسيس_المعرفي/المستوى_الثاني/01_نصوص_الدروس',
             'transcripts/drive-import-2026-11-01/دورة-التأسيس-المعرفى-2-م-أيمن-عبدالرحيم'),
            ('علم_النفس/01_نصوص_الدروس',
             'transcripts/drive-import-2026-11-01/دورة-علم-النفس-م-أيمن-عبد-الرحيم'),
        ]
        for folder, playlist in cases:
            with self.subTest(folder=folder):
                r = subprocess.run([sys.executable, str(TOOLS / 'check_lesson.py'),
                                    str(PKG / folder), '--playlist', playlist],
                                   cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn('ملاحظات: 0', r.stdout)
                for p in (PKG / folder).glob('lesson-*.md'):
                    self.assertIn('غير معتمدة', p.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
