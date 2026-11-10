import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
COURSES = ROOT / '08_دورات_القوائم'
IMPORT = ROOT / 'transcripts/drive-import-2026-11-01'
CHECK = COURSES / 'tools/check_lesson.py'
CASES = [
    ('التأسيس_المعرفي/المستوى_الأول', 'دورة-التأسيس-المعرفى-1-م-أيمن-عبدالرحيم', 8),
    ('التأسيس_المعرفي/المستوى_الثاني', 'دورة-التأسيس-المعرفى-2-م-أيمن-عبدالرحيم', 7),
    ('علم_النفس', 'دورة-علم-النفس-م-أيمن-عبد-الرحيم', 10),
]


class TemplateLessonsTest(unittest.TestCase):
    def test_template_texts(self):
        docs = json.loads((ROOT / '09_تفريغات_أيمن/drive_inventory.json').read_text(encoding='utf-8'))['documents']
        inventory = {d['path']: d for d in docs}
        for course, folder, minimum in CASES:
            scripts = COURSES / course / '01_نصوص_الدروس'
            lessons = sorted(scripts.glob('lesson-[0-9][0-9].md'))
            self.assertEqual(len(lessons), minimum)
            self.assertEqual([int(p.stem[-2:]) for p in lessons], list(range(1, minimum + 1)))
            check = subprocess.run([sys.executable, str(CHECK), str(scripts), '--playlist', str(IMPORT / folder)], text=True, capture_output=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertIn('ملاحظات: 0', check.stdout)
            for lesson in lessons:
                with self.subTest(lesson=lesson):
                    text = lesson.read_text(encoding='utf-8')
                    self.assertIn('معتمد من المالك للنشر', text)
                    headings = ['## افتتاح وخطاف', '## سؤال الدرس', '## مصدر الدرس', '## الكتلة ١', '## الكتلة ٢', '## الكتلة ٣', '## مصيدة', '## المهمة', '## القفلة']
                    positions = [text.index(h) for h in headings]
                    self.assertEqual(positions, sorted(positions))
                    self.assertIn('ما أخذناه', text)
                    self.assertIn('ما أجّلناه', text)
                    for label in ('**مستكشف:**', '**ممارس:**', '**متقدم:**', 'نموذج للمراجعة الذاتية', 'الدرس الجاي', 'استنى هناك'):
                        self.assertIn(label, text)
                    self.assertEqual(text.count('**أداة الكتلة:'), 3)
                    body = re.sub(r'〔[^〕]*〕', ' ', text)
                    body = re.sub(r'\]\([^)]*\)', ']', body)
                    body = re.sub(r'`[^`]*`', ' ', body)
                    self.assertTrue(700 <= len(body.split()) <= 1200, f'{lesson}: {len(body.split())} words')
                    link = re.search(r'\[التفريغ النصي للحلقة \d+\]\(([^)]+)\)', text)
                    self.assertIsNotNone(link)
                    path = (lesson.parent / unquote(link.group(1))).resolve()
                    entry = inventory[str(path.relative_to(ROOT))]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'])
                    self.assertIn(entry['id'], text)
                    citations = re.findall(r'〔ح(\d+) س\d+(?:-\d+)? sha256=([0-9a-f]{64})〕', text)
                    self.assertGreaterEqual(len(citations), 6)
                    self.assertTrue(all(int(ep) == int(lesson.stem[-2:]) and sha == entry['sha256'] for ep, sha in citations))


if __name__ == '__main__':
    unittest.main()
