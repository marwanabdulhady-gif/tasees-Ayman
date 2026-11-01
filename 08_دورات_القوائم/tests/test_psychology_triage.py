import csv
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / '08_دورات_القوائم'
spec = importlib.util.spec_from_file_location('psych_triage', PKG / 'tools/build_psychology_quote_triage.py')
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)


class PsychologyTriageTests(unittest.TestCase):
    def test_queue_regenerates_and_candidates_refer_to_source_lines(self):
        rows, lessons, docs, catalog_sha = triage.build()
        self.assertEqual(len(lessons), 10)
        self.assertEqual(len(docs), 21)
        self.assertTrue(rows)
        with triage.CSV.open(encoding='utf-8', newline='') as f:
            saved = list(csv.DictReader(f))
        self.assertEqual(len(rows), len(saved))
        for row, stored in zip(rows, saved):
            self.assertEqual({k: str(triage.csv_safe(v)) for k, v in row.items()}, stored)
        sources = {d['id']: (ROOT / d['path']).read_text(encoding='utf-8').splitlines() for d in docs}
        for row in rows:
            for field in ('legacy_candidates', 'drive_candidates'):
                for candidate in filter(None, row[field].split('; ')):
                    id_, span = candidate.split(':')
                    bounds = [int(n) for n in span.split('-')]
                    start, end = bounds[0], bounds[-1]
                    self.assertIn(triage.norm(row['quoted_text']),
                                  triage.norm(' '.join(sources[id_][start-1:end])))
        self.assertIn(catalog_sha, triage.REPORT.read_text(encoding='utf-8'))

    def test_spreadsheet_formula_escaping(self):
        for text in ('=1+1', '  +2', '-foo', '@test', '\tformula'):
            self.assertTrue(triage.csv_safe(text).startswith("'"))
        self.assertEqual(triage.csv_safe('نص عادي'), 'نص عادي')


if __name__ == '__main__':
    unittest.main()
