import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
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

    def test_psychology_catalogue_rebuilds_and_preserves_editions(self):
        from ayman_rag.build_psychology_catalog import build
        stored = json.loads((ROOT / 'ayman_rag/psychology_inventory.json').read_text(encoding='utf-8'))
        self.assertEqual(stored, build())
        legacy = [d for d in stored['documents'] if d['id'].startswith('legacy-psy-')]
        drive = [d for d in stored['documents'] if d['id'].startswith('drive-')]
        self.assertEqual((len(drive), len(legacy)), (11, 10))
        self.assertTrue(all(d['speaker_status'] == 'unverified' for d in stored['documents']))
        self.assertTrue(all(d['timestamps'] == 'present_unverified' and d['original_media_url'] for d in legacy))
        self.assertTrue(all(d['original_media_url'] is None for d in drive))
        self.assertEqual(len({d['path'] for d in stored['documents']}), 21)

    def test_real_psychology_index_recovers_both_editions(self):
        from ayman_rag.search import build_index, search
        catalog_path = ROOT / 'ayman_rag/psychology_inventory.json'
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))['documents']
        cases = json.loads((ROOT / 'ayman_rag/psychology_eval_cases.json').read_text(encoding='utf-8'))['cases']
        by_id = {d['id']: d for d in catalog}
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / 'psych.sqlite3'
            self.assertEqual(build_index(catalog_path, index, ROOT)[0], 21)
            for case in cases:
                with self.subTest(case=case['source_id']):
                    doc = by_id[case['source_id']]
                    lines = (ROOT / doc['path']).read_text(encoding='utf-8').splitlines()
                    self.assertIn(case['quote'], lines[case['line'] - 1])
                    # Constraining by the already-known source tests retrieval
                    # and exact evidence, not general retrieval relevance.
                    results = search(case['query'], index_path=index, catalog_path=catalog_path,
                                     root=ROOT, source_id=case['source_id'], limit=50)
                    self.assertTrue(any(r['start_line'] <= case['line'] <= r['end_line'] for r in results))
                    self.assertTrue(all(r['source_id'] == case['source_id'] for r in results))
                    self.assertTrue(all(r['speaker_status'] == 'unverified' for r in results))
            model = Path(temp) / 'model.gguf'
            model.write_bytes(b'not a real model')
            runner = Path(temp) / 'stub-llama'
            runner.write_text('#!/usr/bin/env python3\nprint("مسودة تجريبية [S1]")\n', encoding='utf-8')
            runner.chmod(0o755)
            legacy = next(c for c in cases if c['source_id'].startswith('legacy-psy-'))
            run = subprocess.run([sys.executable, str(ROOT / 'ayman_rag/answer.py'), legacy['query'],
                                  '--model', str(model), '--llama-cli', str(runner),
                                  '--catalog', str(catalog_path), '--index', str(index),
                                  '--source-id', legacy['source_id']], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn(by_id[legacy['source_id']]['path'], run.stdout)
            self.assertIn('رابط تسجيل مذكور', run.stdout)
            self.assertIn('مسودة تجريبية [S1]', run.stdout)

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
