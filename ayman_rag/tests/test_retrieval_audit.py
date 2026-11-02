import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ayman_rag.audit_playlist_retrieval import OUTPUT_JSON, OUTPUT_MD, build  # noqa: E402
from ayman_rag.search import ROOT as SEARCH_ROOT, build_index  # noqa: E402
from ayman_rag.build_playlist_catalog import OUTPUT as CATALOG  # noqa: E402

SCRIPT = ROOT / 'ayman_rag' / 'audit_playlist_retrieval.py'


class RetrievalAuditTests(unittest.TestCase):
    def test_report_is_reproducible_and_all_plumbing_checks_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / 'playlists.sqlite3'
            build_index(CATALOG, index, SEARCH_ROOT)
            report, md = build(index_path=index)
            self.assertEqual(report['status'], 'pass')
            self.assertEqual(report['catalog']['documents'], 398)
            self.assertEqual(report['catalog']['playlist_sources'], 240)
            self.assertEqual(report['catalog']['playlists'], 11)
            self.assertEqual(report['catalog']['unassigned_drive_sources'], 158)
            self.assertTrue(all(c['status'] == 'pass' for c in report['checks']))
            self.assertEqual(len(report['results']['filter_isolation']), 11)
            self.assertEqual(len(report['results']['cross_playlist_leakage']), 11)
            self.assertTrue(all(r['all_results_in_requested_playlist']
                                for r in report['results']['filter_isolation']))
            self.assertTrue(all(r['expected_source_absent']
                                for r in report['results']['cross_playlist_leakage']))
            self.assertEqual(report['results']['unknown_playlist_slug']['results'], 0)
            self.assertEqual(report['results']['negative_control']['results'], 0)
            self.assertEqual(report['results']['known_location']['hits'], 11)
            self.assertEqual(report['results']['known_location']['total'], 11)
            self.assertGreaterEqual(len(report['limits']), 4)
            self.assertIn('not semantic', ' '.join(report['limits']))
            self.assertEqual(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                             OUTPUT_JSON.read_text(encoding='utf-8'))
            self.assertEqual(md, OUTPUT_MD.read_text(encoding='utf-8'))
            r = subprocess.run([sys.executable, str(SCRIPT), '--check', '--index', str(index)],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('ok:', r.stdout)


if __name__ == '__main__':
    unittest.main()
