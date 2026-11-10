import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '08_دورات_القوائم' / 'tools'


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ManualReviewReportsTest(unittest.TestCase):
    def test_overlap_report_is_reproducible_and_verified(self):
        mod = load('build_foundation_overlap_report')
        self.assertEqual(mod.OUT.read_text(encoding='utf-8'), mod.build())
        self.assertIn('44.5%', mod.build())

    def test_psychology_report_is_reproducible_and_complete(self):
        mod = load('render_psychology_review')
        self.assertEqual(mod.OUT.read_text(encoding='utf-8'), mod.build())
        self.assertIn('فُرزت 0 واقعة', mod.build())

    def test_changed_queue_or_lesson_is_rejected(self):
        mod = load('render_psychology_review')
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            shutil.copytree(mod.COURSE / 'الدروس', temp / 'الدروس')
            queue = temp / mod.QUEUE.name
            review = temp / mod.REVIEW.name
            shutil.copy(mod.QUEUE, queue)
            shutil.copy(mod.REVIEW, review)
            with patch.object(mod, 'COURSE', temp), patch.object(mod, 'QUEUE', queue), patch.object(mod, 'REVIEW', review):
                self.assertTrue(mod.build())
                queue.write_bytes(queue.read_bytes() + b'\n')
                with self.assertRaisesRegex(ValueError, 'Queue changed'):
                    mod.build()
                shutil.copy(ROOT / '08_دورات_القوائم/علم_النفس/05_طابور_مراجعة_الاقتباسات.csv', queue)
                lesson = next((temp / 'الدروس').glob('01_*.md'))
                lesson.write_bytes(lesson.read_bytes() + b'\n')
                with self.assertRaisesRegex(ValueError, 'Lesson changed'):
                    mod.build()


if __name__ == '__main__':
    unittest.main()
