import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('course_check', ROOT / '08_دورات_القوائم/tools/check_playlist_course.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LineCitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pkg = self.root / 'courses'
        self.course = self.pkg / 'example'
        self.course.mkdir(parents=True)
        self.source = self.root / 'source.txt'
        self.source.write_text('أول سطر عربي\nثاني سطر مفيد\nثالث سطر أخير\n', encoding='utf-8')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.reg = [{'slug': 'test', 'course_dir': 'example', 'items': [{'n': 1, 'file': 'source.txt', 'sha': self.digest[:16], 'timestamps': True, 'title': 'test'}]}]
        self.idea = {'text': 'فكرة', 'ep': 1, 'cite': 'L2', 'quote': 'ثاني سطر مفيد', 'source_sha256': self.digest}
        self.map = {'slug': 'test', 'status': 'خريطة', 'voice': 'ayman', 'built_from': {'1': self.digest[:16]}, 'lessons': [{'n': 1, 'episodes': [1], 'ideas': [self.idea, self.idea, self.idea], 'patterns': ['P01', 'P02'], 'hook': 'دفتر'}]}
        (self.pkg / 'playlists.json').write_text(json.dumps({'playlists': self.reg}), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        (self.course / '00_خريطة_الدورة.json').write_text(json.dumps(self.map), encoding='utf-8')
        output = io.StringIO()
        with patch.object(checker, 'ROOT', self.root), patch.object(checker, 'PKG', self.pkg), contextlib.redirect_stdout(output):
            code = checker.main(['check', 'test'])
        return code, output.getvalue()

    def test_valid_single_line_and_range(self):
        self.assertEqual(self.check()[0], 0)
        self.idea.update(cite='L1-L2', quote='أول سطر عربي\nثاني سطر مفيد')
        self.assertEqual(self.check()[0], 0)

    def test_wrong_range_quote_and_missing_quote(self):
        for change in ({'cite': 'L1'}, {'quote': ''}, {'quote': 'ثاني سطر مختلف'}, {'quote': 'ثاني سطر مُفيد'}, {'cite': 'L0'}, {'cite': 'L2-L1'}, {'cite': 'L2-L4'}, {'cite': 'L2-L12'}):
            with self.subTest(change=change):
                old = self.idea.copy()
                self.idea.update(change)
                self.assertEqual(self.check()[0], 1)
                self.idea.clear(); self.idea.update(old)

    def test_changed_source_and_stale_registry(self):
        self.source.write_text('أول سطر عربي\nثاني سطر مفيد\nتغيير\n', encoding='utf-8')
        self.assertIn('source_sha256 does not match', self.check()[1])
        self.idea['source_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertIn('episode registry is stale', self.check()[1])
        self.assertEqual(self.check()[0], 1)

    def test_missing_or_short_hash(self):
        for sha in (None, self.digest[:16], self.digest.upper()):
            with self.subTest(sha=sha):
                self.idea['source_sha256'] = sha
                self.assertEqual(self.check()[0], 1)

    def test_existing_timestamp_and_paragraph_checks_still_apply(self):
        self.source.write_text('**[01:15] أول سطر عربي\n\nثاني سطر مفيد\n', encoding='utf-8')
        self.idea.clear(); self.idea.update(text='فكرة', ep=1, cite='01:15', quote='أول سطر عربي')
        self.assertEqual(self.check()[0], 0)
        self.idea['cite'] = '20:00'
        self.assertEqual(self.check()[0], 1)
        self.idea.update(cite='¶2', quote='ثاني سطر مفيد')
        self.assertEqual(self.check()[0], 0)
        self.idea['cite'] = '¶1'
        self.assertEqual(self.check()[0], 1)


if __name__ == '__main__':
    unittest.main()
