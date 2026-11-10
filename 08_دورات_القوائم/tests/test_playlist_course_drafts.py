# -*- coding: utf-8 -*-
"""Checks for the separate all-playlist owner-approved course shelf.

These checks prove structural coverage, exact source hashes and generated-file
reproducibility. The owner has approved publication in the repository; they do
not independently verify content, voice, recordings, references or specialist
review, and they do not create official course maps.
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
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / '08_دورات_القوائم'
TOOLS = PKG / 'tools'
SHELF = PKG / '10_مسودات_القوائم'
CATALOG = ROOT / 'ayman_rag' / 'playlist_inventory.json'
REGISTRY = PKG / 'playlists.json'
OFFICIAL_MAPS = [
    (PKG / 'التأسيس_المعرفي/المستوى_الأول/00_خريطة_الدورة.json', 'خريطة معتمدة من المالك'),
    (PKG / 'التأسيس_المعرفي/المستوى_الثاني/00_خريطة_الدورة.json', 'خريطة معتمدة من المالك'),
    (PKG / 'علم_النفس/00_خريطة_الدورة.json', 'نصوص بلا خريطة معتمدة من المالك'),
]


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *args], cwd=ROOT,
                          capture_output=True, text=True)


def lesson_links(text):
    return re.findall(r'\[التفريغ النصي للحلقة [٠-٩\d]+\]\(([^)]+)\)', text)


class AllPlaylistDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = json.loads((SHELF / '00_حالة_القوائم.json').read_text(encoding='utf-8'))
        cls.catalog = {d['id']: d for d in json.loads(CATALOG.read_text(encoding='utf-8'))['documents']}
        cls.by_path = {d['path']: d for d in cls.catalog.values()}
        cls.registry = json.loads(REGISTRY.read_text(encoding='utf-8'))['playlists']

    def groups_for(self, count):
        size = 1 if count <= 10 else 3 if count <= 20 else 4
        return [list(range(i + 1, min(i + size, count) + 1)) for i in range(0, count, size)]

    def test_catalog_and_generators_are_reproducible(self):
        r = run(ROOT / 'ayman_rag/build_playlist_catalog.py', '--check')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for script in ('build_playlist_course_drafts.py', 'build_playlist_course_screens.py',
                       'build_review_queue.py'):
            with self.subTest(script=script):
                r = run(TOOLS / script, '--check')
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        docs = list(self.catalog.values())
        self.assertEqual(len(docs), 398)
        self.assertEqual(len({d['path'] for d in docs}), 398)
        playlist_docs = [d for d in docs if d.get('playlist_slug')]
        self.assertEqual(len(playlist_docs), 240)
        self.assertEqual(self.state['totals'], {'playlists': 11, 'sources': 240,
                                                'lessons': 99, 'screens': 990})

    def test_every_registered_playlist_is_covered(self):
        self.assertEqual(len(self.state['playlists']), 11)
        for pl in self.registry:
            with self.subTest(playlist=pl['slug']):
                course = SHELF / pl['slug']
                summary = next(x for x in self.state['playlists'] if x['slug'] == pl['slug'])
                groups = self.groups_for(len(pl['items']))
                lessons = sorted((course / '01_نصوص_الدروس').glob('lesson-[0-9][0-9].md'))
                screens = sorted((course / '02_الشاشات').glob('lesson-[0-9][0-9].html'))
                self.assertEqual((len(lessons), len(screens), summary['lessons']),
                                 (len(groups), len(groups), len(groups)))
                self.assertEqual(summary['screens'], len(groups) * 10)
                self.assertEqual([int(p.stem[-2:]) for p in lessons], list(range(1, len(groups) + 1)))
                cmap = json.loads((course / '00_خريطة_المسودة.json').read_text(encoding='utf-8'))
                self.assertEqual(cmap['status'], 'معتمد من المالك للنشر')
                self.assertEqual([l['episodes'] for l in cmap['lessons']], groups)
                self.assertFalse((course / '00_خريطة_الدورة.json').exists())
                self.assertTrue((course / 'README.md').is_file())
                self.assertTrue((course / '00_فهرس_المسودة.md').is_file())
                index = (course / '02_الشاشات/index.html').read_text(encoding='utf-8')
                for n in range(1, len(groups) + 1):
                    self.assertIn(f'lesson-{n:02d}.html', index)
                    self.assertIn(f'../01_نصوص_الدروس/lesson-{n:02d}.md', index)
                self.assertTrue((course / '00_طابور_المراجعة.md').is_file())
                self.assertIn('00_طابور_المراجعة.md', (course / 'README.md').read_text(encoding='utf-8'))
                self.assertIn('../00_طابور_المراجعة.md', index)
                self.assertIn('../../03_لوحة_المراجعة/index.html', index)

    def test_check_lesson_passes_for_all_eleven_source_directories(self):
        for pl in self.registry:
            with self.subTest(playlist=pl['slug']):
                lessons = SHELF / pl['slug'] / '01_نصوص_الدروس'
                source_dir = (ROOT / pl['items'][0]['file']).parent
                r = run(TOOLS / 'check_lesson.py', str(lessons), '--playlist', str(source_dir))
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn('ملاحظات: 0', r.stdout)

    def test_lessons_follow_template_and_match_source_bytes(self):
        headings = ['## افتتاح وخطاف', '## سؤال الدرس', '## مصدر الدرس',
                    '## الكتلة ١', '## الكتلة ٢', '## الكتلة ٣',
                    '## مصيدة الفهم', '## المهمة', '## القفلة']
        for pl in self.registry:
            for lesson in sorted((SHELF / pl['slug'] / '01_نصوص_الدروس').glob('lesson-*.md')):
                with self.subTest(lesson=str(lesson.relative_to(ROOT))):
                    text = lesson.read_text(encoding='utf-8')
                    self.assertIn('معتمد من المالك للنشر', text)
                    positions = [text.index(h) for h in headings]
                    self.assertEqual(positions, sorted(positions))
                    self.assertEqual(text.count('«'), 6)
                    self.assertEqual(text.count('〔'), 6)
                    self.assertEqual(text.count('**أداة الكتلة:'), 3)
                    for label in ('**مستكشف:**', '**ممارس:**', '**متقدم:**',
                                  'نموذج للمراجعة الذاتية', 'الدرس الجاي', 'استنى هناك'):
                        self.assertIn(label, text)
                    body = re.sub(r'〔[^〕]*〕', ' ', text)
                    body = re.sub(r'\]\([^)]*\)', ']', body)
                    body = re.sub(r'`[^`]*`', ' ', body)
                    self.assertTrue(700 <= len(body.split()) <= 1200)
                    ids = re.findall(r'معرّف المصدر `([^`]+)`', text)
                    shas = re.findall(r'SHA-256\s+`([0-9a-f]{64})`', text)
                    links = lesson_links(text)
                    self.assertEqual(len(ids), len(shas))
                    self.assertEqual(len(ids), len(links))
                    self.assertTrue(ids)
                    for id_, sha, link in zip(ids, shas, links):
                        self.assertIn(id_, self.catalog)
                        source = (lesson.parent / unquote(link)).resolve()
                        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), sha)
                        self.assertEqual(self.by_path[str(source.relative_to(ROOT))]['sha256'], sha)
                        self.assertEqual(self.catalog[id_]['sha256'], sha)
                    if pl.get('voice') == 'owner-decision':
                        self.assertIn('مرشد الدورة', text)
                        self.assertIn('لا تطابق Q1', text)
                        self.assertNotIn('أهلًا بيك', text)
                        self.assertRegex(text, r'وليس(?:ت منسوبة|\s*منسوبًا) إلى أيمن عبد الرحيم')
                    if pl['slug'] == 'ayn-al-tariq':
                        self.assertIn('〔ح', text)
                        self.assertRegex(text, r'〔ح[٠-٩\d]+\s+ص[٠-٩\d]+〕')

    def test_screens_match_lessons_catalog_and_template(self):
        for pl in self.registry:
            course = SHELF / pl['slug']
            for lesson in sorted((course / '01_نصوص_الدروس').glob('lesson-*.md')):
                with self.subTest(lesson=str(lesson.relative_to(ROOT))):
                    n = int(lesson.stem[-2:])
                    page = course / '02_الشاشات' / f'lesson-{n:02d}.html'
                    html = page.read_text(encoding='utf-8')
                    data = json.loads(re.search(r'<script type="application/json" id="week">\n(.*?)\n</script>',
                                                html, re.S).group(1))
                    text = lesson.read_text(encoding='utf-8')
                    ids = re.findall(r'معرّف المصدر `([^`]+)`', text)
                    shas = re.findall(r'SHA-256\s+`([0-9a-f]{64})`', text)
                    links = lesson_links(text)
                    self.assertEqual(data['week'], n)
                    self.assertEqual(data['lesson'], n)
                    self.assertEqual(data['source_ids'], ids)
                    self.assertEqual(data['source_shas'], shas)
                    self.assertEqual(data['source_links'], links)
                    self.assertEqual(data['source_sha'],
                                     hashlib.sha256('\n'.join(shas).encode('utf-8')).hexdigest())
                    self.assertEqual(len(data['screens']), 10)
                    self.assertEqual(data['screens'][0]['layout'], 'L1')
                    self.assertEqual(data['screens'][-1]['layout'], 'L7')
                    self.assertTrue({'P14', 'P02', 'P17', 'P15'} <=
                                    {s.get('pattern') for s in data['screens']})
                    self.assertIn('معتمد من المالك للنشر', data['draft'])
                    self.assertTrue((page.parent / data['text_href']).exists())
                    for rel in re.findall(r'<(?:link|script)[^>]*?(?:href|src)="([^"]+)"', html):
                        if rel.startswith('http') or rel.startswith('#'):
                            continue
                        self.assertTrue((page.parent / rel.split('#')[0]).resolve().exists(),
                                        f'{page.name}: {rel}')

    def test_review_board_is_linked_and_state_points_to_it(self):
        self.assertEqual(self.state['review_status'],
                         'approved; owner decision recorded; independent verification owner_accepted_unverified')
        self.assertEqual(self.state['rag_audit'], 'ayman_rag/playlist_retrieval_audit.json')
        self.assertTrue((SHELF / '00_طابور_المراجعة.json').is_file())
        self.assertTrue((SHELF / '00_طابور_المراجعة.md').is_file())
        board = SHELF / '03_لوحة_المراجعة/index.html'
        self.assertTrue(board.is_file())
        self.assertIn('قرار المالك موثق', board.read_text(encoding='utf-8'))
        root_readme = (SHELF / 'README.md').read_text(encoding='utf-8')
        self.assertIn('00_طابور_المراجعة.md', root_readme)
        self.assertIn('03_لوحة_المراجعة/index.html', root_readme)
        shelf_index = (SHELF / 'index.html').read_text(encoding='utf-8')
        self.assertIn('03_لوحة_المراجعة/index.html', shelf_index)

    def test_official_maps_are_untouched(self):
        for path, status in OFFICIAL_MAPS:
            with self.subTest(map=str(path.relative_to(ROOT))):
                cmap = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(cmap['status'], status)
        self.assertFalse((SHELF / '00_خريطة_الدورة.json').exists())

    @unittest.skipUnless(shutil.which('node'), 'node is not installed')
    def test_inline_scripts_parse(self):
        pages = sorted(SHELF.glob('*/02_الشاشات/lesson-*.html'))
        self.assertEqual(len(pages), 99)
        with tempfile.TemporaryDirectory() as tmp:
            for i, page in enumerate(pages):
                html = page.read_text(encoding='utf-8')
                scripts = re.findall(r'<script(?![^>]*type="application/json")(?![^>]*src)[^>]*>(.*?)</script>',
                                     html, re.S)
                self.assertEqual(len(scripts), 1, page.name)
                js = Path(tmp) / f'{i}.js'
                js.write_text(scripts[0], encoding='utf-8')
                r = subprocess.run(['node', '--check', str(js)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, page.name + ': ' + r.stderr)


if __name__ == '__main__':
    unittest.main()
