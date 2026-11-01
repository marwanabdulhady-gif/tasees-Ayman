import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / '08_دورات_القوائم/tools/check_lesson.py'


class TextLessonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.source_dir, self.lessons = base / 'sources', base / 'lessons'
        self.source_dir.mkdir(); self.lessons.mkdir()
        self.source = self.source_dir / '001 - test.txt'
        self.source.write_text('تمهيد قصير هنا\nهذه جملة حرفية واضحة\nالنهاية في سطر آخر\n', encoding='utf-8')
        self.sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.lesson = self.lessons / '01_draft.md'

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, citations):
        headings = '\n'.join('## ' + title for title in ['سؤال الدرس', 'مصدر الدرس', 'الكتلة ١', 'الكتلة ٢', 'الكتلة ٣', 'مصيدة', 'المهمة', 'القفلة'])
        self.lesson.write_text(headings + '\n' + '\n'.join(citations) + '\n', encoding='utf-8')
        return subprocess.run([sys.executable, str(CHECK), str(self.lessons), '--playlist', str(self.source_dir)], capture_output=True, text=True)

    def valid(self, n='١', span='٢', sha=None, quote='هذه جملة حرفية واضحة'):
        return f'«{quote}» 〔ح{n} س{span} sha256={sha or self.sha}〕'

    def test_exact_citations_and_ranges(self):
        r = self.run_check([self.valid()] * 5 + [self.valid(span='١-٢')])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_wrong_line_quote_episode_hash_and_format_fail(self):
        invalid = [self.valid(span='١'), self.valid(span='٠'), self.valid(span='٢-٤'),
                   self.valid(n='٢'), self.valid(quote='هذه جملة حَرفية واضحة'),
                   self.valid(sha='0' * 64), '〔ح١ س٢〕', '〔ح١ س٢',
                   f'〔ح١ س٢ sha256={self.sha}〕']
        for bad in invalid:
            with self.subTest(bad=bad):
                r = self.run_check([self.valid()] * 6 + [bad])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_changed_bytes_and_timestamps_rejected(self):
        citation = self.valid()
        self.source.write_text(self.source.read_text() + 'تغيير\n', encoding='utf-8')
        r = self.run_check([citation] * 6)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('بصمة', r.stdout)
        r = self.run_check(['〔ح١ 00:01〕'] * 6)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('بلا توقيتات', r.stdout)

    def test_spec_template_names_and_missing_lesson_filter(self):
        self.run_check([self.valid()] * 6)
        self.lesson.rename(self.lessons / 'lesson-01.md')
        cmd = [sys.executable, str(CHECK), str(self.lessons), '--playlist', str(self.source_dir)]
        r = subprocess.run(cmd + ['--lesson', '01'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        missing = subprocess.run(cmd + ['--lesson', '02'], capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertIn('لا دروس', missing.stdout)

    def test_number_notes_ignore_metadata_but_not_visible_claims(self):
        metadata = f'المصدر [رابط](https://example.com/2026/%D8%88) SHA-256 `{self.sha}`'
        r = self.run_check([self.valid()] * 6 + [metadata, 'النتيجة المزعومة 987654'])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('987654', r.stdout)
        self.assertNotIn('2026', r.stdout)
        self.assertNotIn('256', r.stdout)
        self.assertNotIn('«88»', r.stdout)
        r = self.run_check([self.valid()] * 6 + ['[987654](https://example.com/2026)'])
        self.assertIn('987654', r.stdout)

    def test_two_quotes_or_two_citations_on_one_line_fail(self):
        for bad in (self.valid() + ' «نهاية أخرى مفيدة»', self.valid() + ' ' + self.valid()):
            r = self.run_check([self.valid()] * 6 + [bad])
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_legacy_timestamped_markdown_still_passes(self):
        self.source.unlink()
        (self.source_dir / '01 - test.md').write_text('**[00:01](https://example.com)** هذه جملة حرفية واضحة\n', encoding='utf-8')
        r = self.run_check(['«هذه جملة حرفية واضحة» 〔ح١ 00:01〕'] * 6)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
