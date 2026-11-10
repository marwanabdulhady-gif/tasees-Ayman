import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / '08_دورات_القوائم'


class FoundationSampleTests(unittest.TestCase):
    def test_partial_maps_validate_against_original_files(self):
        for slug, folder in [('cognitive-foundation-1', 'المستوى_الأول'),
                             ('cognitive-foundation-2', 'المستوى_الثاني')]:
            with self.subTest(slug=slug):
                path = PKG / 'التأسيس_المعرفي' / folder / '00_خريطة_الدورة.json'
                cmap = json.loads(path.read_text(encoding='utf-8'))
                self.assertTrue(cmap['lessons'])
                self.assertTrue(all(i['cite'].startswith('L') for lesson in cmap['lessons'] for i in lesson['ideas']))
                result = subprocess.run([sys.executable, str(PKG / 'tools/check_playlist_course.py'), slug],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
