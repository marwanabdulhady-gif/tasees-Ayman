import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from ayman_rag.compare import compare_sources, compare_texts, tokens_by_line


class ComparisonTests(unittest.TestCase):
    def test_shared_runs_and_original_line_ranges(self):
        a = 'تمهيد مختلف\nواحد اثنان ثلاثة اربعة خمسة ستة سبعة ثمانية تسعة عشرة احد عشر اثنا عشر\nنهاية اخرى\n'
        b = 'افتتاح اخر\nواحد اثنان ثلاثة اربعة خمسة ستة سبعة ثمانية تسعة عشرة احد عشر اثنا عشر\nختام مختلف\n'
        r = compare_texts(a, b)
        self.assertGreater(r['shared_unique_shingles'], 0)
        self.assertEqual((r['unique_anchor_runs'][0]['a_start_line'], r['unique_anchor_runs'][0]['a_end_line']), (2, 2))
        self.assertEqual((r['unique_anchor_runs'][0]['b_start_line'], r['unique_anchor_runs'][0]['b_end_line']), (2, 2))
        self.assertEqual(r['unique_anchor_runs'][0]['words'], 14)
        self.assertEqual(sum(x['total'] for x in r['a_position_bins']), r['a_tokens'] - 4)
        reverse = compare_texts(b, a)
        self.assertEqual(r['shared_unique_shingles'], reverse['shared_unique_shingles'])
        self.assertEqual(r['unique_jaccard'], reverse['unique_jaccard'])

    def test_no_match_short_inputs_and_limits(self):
        self.assertEqual(compare_texts('ا ب ج د ه', 'ك ل م ن س')['shared_unique_shingles'], 0)
        self.assertIsNone(compare_texts('نص قصير', 'نص قصير')['unique_jaccard'])
        with self.assertRaises(ValueError):
            compare_texts('ا ب ج د ه', 'ا ب ج د ه', max_runs=51)
        self.assertEqual(compare_texts('ا ب ج د ه', 'ا ب ج د ه', max_runs=0)['unique_anchor_runs'], [])

    def test_metadata_links_do_not_distort_tokens(self):
        w, lines = tokens_by_line('**[01:15](https://example.com/a)** هذه جملة أصلية واضحة\n')
        self.assertEqual(w, ['هذه', 'جمله', 'اصليه', 'واضحه'])
        self.assertEqual(lines, [1, 1, 1, 1])

    def test_catalog_hash_and_path_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'transcripts/drive-import-2026-11-01/folder'
            folder.mkdir(parents=True)
            docs = []
            for name in ('a', 'b'):
                p = folder / f'{name}.txt'
                p.write_text('واحد اثنان ثلاثة اربعة خمسة ستة سبعة ثمانية تسعة عشرة\n', encoding='utf-8')
                docs.append({'id': name, 'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
            cat = root / 'cat.json'; cat.write_text(json.dumps({'documents': docs}))
            result = compare_sources('a', 'b', cat, root)
            self.assertEqual(result['unique_jaccard'], 1.0)
            (folder / 'a.txt').write_text('modified')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                compare_sources('a', 'b', cat, root)
            with self.assertRaisesRegex(ValueError, 'distinct'):
                compare_sources('a', 'a', cat, root)
            with self.assertRaisesRegex(ValueError, 'unknown'):
                compare_sources('a', 'missing', cat, root)


if __name__ == '__main__':
    unittest.main()
