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
    ('التأسيس_المعرفي/المستوى_الأول/مسودات_الدروس', 'دورة-التأسيس-المعرفى-1-م-أيمن-عبدالرحيم', 4),
    ('التأسيس_المعرفي/المستوى_الثاني/مسودات_الدروس', 'دورة-التأسيس-المعرفى-2-م-أيمن-عبدالرحيم', 2),
    ('علم_النفس/مسودات_الدروس', 'دورة-علم-النفس-م-أيمن-عبد-الرحيم', 1),
]


class DraftLessonsTest(unittest.TestCase):
    def test_drafts_pass_and_sources_match_import_inventory(self):
        catalog = json.loads((ROOT / '09_تفريغات_أيمن/drive_inventory.json').read_text(encoding='utf-8'))
        by_path = {d['path']: d for d in catalog['documents']}
        for course, folder, count in CASES:
            draft_dir = COURSES / course
            lessons = sorted(draft_dir.glob('[0-9][0-9]_*.md'))
            self.assertGreaterEqual(len(lessons), count)
            result = subprocess.run([sys.executable, str(CHECK), str(draft_dir), '--playlist', str(IMPORT / folder)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('ملاحظات: 0', result.stdout)
            for lesson in lessons:
                text = lesson.read_text(encoding='utf-8')
                self.assertIn('غير معتمدة', text)
                self.assertIn('نموذج للمراجعة الذاتية', text)
                link = re.search(r'\[التفريغ النصي للحلقة \d+\]\(([^)]+)\)', text)
                self.assertIsNotNone(link, lesson)
                source = (lesson.parent / unquote(link.group(1))).resolve()
                rel = str(source.relative_to(ROOT))
                entry = by_path[rel]
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                self.assertEqual(digest, entry['sha256'])
                self.assertIn(entry['id'], text)
                cites = re.findall(r'〔ح(\d+) س\d+(?:-\d+)? sha256=([0-9a-f]{64})〕', text)
                self.assertGreaterEqual(len(cites), 6)
                self.assertTrue(all(int(ep) == int(lesson.name[:2]) and sha == digest for ep, sha in cites))


if __name__ == '__main__':
    unittest.main()
