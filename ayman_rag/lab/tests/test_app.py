"""Run with:  python -m unittest discover tests   (or: pytest)"""

import tempfile
import unittest
from pathlib import Path

from src.chunking.chunker import chunk_lecture
from src.ingestion.loader import Lecture, Paragraph, parse_transcript
from src.retrieval.evaluate import first_hit_rank
from src.retrieval.retriever import BM25Retriever
from src.utils.helpers import normalize_arabic

SAMPLE = """# دورة علم النفس  المحاضرة الأولي

- الحلقة: 1
- الرابط: https://www.youtube.com/watch?v=abc

---

**[00:18](https://www.youtube.com/watch?v=abc&t=18s)** بسم الله نبدأ دورة علم النفس

**[1:01:48](https://www.youtube.com/watch?v=abc&t=3708s)** الوعي اللغوي مهم جدا
"""


class TestNormalize(unittest.TestCase):
    def test_alef_and_tashkeel(self):
        self.assertEqual(normalize_arabic("الإِسْلَام"), normalize_arabic("الاسلام"))

    def test_taa_marbuta_matches_captions(self):
        self.assertEqual(normalize_arabic("المحاضرة"), "المحاضره")


class TestLoader(unittest.TestCase):
    def test_parse_transcript(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "01.md"
            path.write_text(SAMPLE, encoding="utf-8")
            lec = parse_transcript(path, "03-psychology")
        self.assertEqual(lec.title, "دورة علم النفس المحاضرة الأولي")
        self.assertEqual(lec.number, 1)
        self.assertEqual([p.start_seconds for p in lec.paragraphs], [18, 3708])


class TestChunker(unittest.TestCase):
    def make_lecture(self, n_paras=20, words_each=50):
        paras = [Paragraph(i * 60, " ".join(["كلمه"] * words_each)) for i in range(n_paras)]
        return Lecture("c", 1, "t", "https://youtu.be/x?v=1", paras)

    def test_chunks_cover_lecture_with_overlap(self):
        chunks = chunk_lecture(self.make_lecture(), chunk_words=200, overlap_words=50)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].start_seconds, 0)
        # Second chunk starts one paragraph (50 words) before the first chunk ended.
        self.assertEqual(chunks[1].start_seconds, 3 * 60)
        self.assertTrue(chunks[1].url.endswith("&t=180s"))

    def test_chunk_never_empty_when_paragraph_is_huge(self):
        lec = self.make_lecture(n_paras=3, words_each=1000)
        chunks = chunk_lecture(lec, chunk_words=200, overlap_words=50)
        self.assertEqual(len(chunks), 3)


class TestBM25(unittest.TestCase):
    def test_finds_matching_chunk(self):
        lec = Lecture("c", 1, "t", "", [
            Paragraph(0, "حديث عن التاريخ الاموي والعباسي"),
            Paragraph(60, "حديث عن الوعي اللغوي والكلمات"),
        ])
        chunks = chunk_lecture(lec, chunk_words=3, overlap_words=0)
        best, _ = BM25Retriever(chunks).search("ما هو الوعي اللغوي؟", 1)[0]
        self.assertIn("اللغوي", best.text)


class TestEvaluate(unittest.TestCase):
    def test_first_hit_rank(self):
        lec = Lecture("c", 7, "t", "", [Paragraph(0, "ا ب ج")])
        results = [(chunk_lecture(lec)[0], 1.0)]
        self.assertEqual(first_hit_rank(results, {"c/7"}), 1)
        self.assertIsNone(first_hit_rank(results, {"c/8"}))


if __name__ == "__main__":
    unittest.main()
