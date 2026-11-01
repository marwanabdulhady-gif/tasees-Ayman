import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / '09_تفريغات_أيمن/drive_inventory.json'
COURSE = ROOT / '08_دورات_القوائم/التأسيس_المعرفي/00_جرد_وهيكل_أولي.md'


class CorpusTests(unittest.TestCase):
    def test_inventory_regenerates_exactly(self):
        spec = importlib.util.spec_from_file_location('inventory', ROOT / '09_تفريغات_أيمن/tools/build_drive_inventory.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        stored = json.loads(CATALOG.read_text(encoding='utf-8'))
        self.assertEqual(stored, mod.build())
        self.assertEqual(len(stored['documents']), 173)
        self.assertTrue(all(d['speaker_status'] == 'unverified' for d in stored['documents']))

    def test_course_anchors_and_excerpts(self):
        docs = {d['id']: d for d in json.loads(CATALOG.read_text(encoding='utf-8'))['documents']}
        pattern = r'\|\s*[12]\s*\|\s*\d{3}\s*\|[^|]+\|\s*«([^»]+)»\s*\|\s*\[السطر (\d+)\]\(([^)]+)\) · `(drive-[0-9a-f]+)`'
        found = re.findall(pattern, COURSE.read_text(encoding='utf-8'))
        self.assertEqual(len(found), 15)
        for excerpt, line, link, id_ in found:
            path, fragment = unquote(link).rsplit('#', 1)
            p = (COURSE.parent / path).resolve()
            doc = docs[id_]
            self.assertEqual(p, (ROOT / doc['path']).resolve())
            self.assertEqual(fragment, f'L{line}')
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), doc['sha256'])
            self.assertIn(excerpt, p.read_text(encoding='utf-8').splitlines()[int(line)-1])


if __name__ == '__main__':
    unittest.main()
