import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from ayman_rag.search import build_index, chunks, normalize, search


class OfflineSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'transcripts/drive-import-2026-11-01/test/lecture.txt'
        self.source.parent.mkdir(parents=True)
        self.text = 'مُقَدِّمة عن المعرفة\nهذه سطور عن الشك المنهجي وفهم النفس.\nخاتمة الدرس.\n'
        self.source.write_text(self.text, encoding='utf-8')
        self.catalog = self.root / 'catalog.json'
        self.index = self.root / '.cache/test.sqlite3'
        self.doc = {'id': 'drive-test', 'path': str(self.source.relative_to(self.root)),
                    'sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                    'title': 'اختبار', 'folder': 'test', 'source_folder_url': 'https://drive.google.com/drive/folders/example'}
        self.write_catalog()
        build_index(self.catalog, self.index, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def write_catalog(self):
        self.catalog.write_text(json.dumps({'documents': [self.doc]}), encoding='utf-8')

    def find(self, query):
        return search(query, self.index, root=self.root, catalog_path=self.catalog)

    def test_normalization_without_modifying_source(self):
        self.assertEqual(normalize('إِسلاميّة'), 'اسلاميه')
        r = self.find('المعرفه')[0]
        self.assertIn('مُقَدِّمة عن المعرفة', r['excerpt'])
        self.assertEqual(self.source.read_text(), self.text)

    def test_source_span_is_exact(self):
        r = self.find('الشك المنهجي')[0]
        self.assertEqual(r['excerpt'], ''.join(self.text.splitlines(keepends=True)[r['start_line']-1:r['end_line']]).strip())
        self.assertEqual(r['speaker_status'], 'unverified')

    def test_folder_filter_is_exact(self):
        self.assertEqual(len(search('الشك', self.index, root=self.root, catalog_path=self.catalog, folder='test')), 1)
        self.assertEqual(search('الشك', self.index, root=self.root, catalog_path=self.catalog, folder='other'), [])

    def test_source_filter_and_all_terms(self):
        other = self.root / 'transcripts/drive-import-2026-11-01/test/other.txt'
        other.write_text('الشك وحده في نص آخر.\n', encoding='utf-8')
        doc2 = dict(self.doc, id='drive-other', path=str(other.relative_to(self.root)),
                    sha256=hashlib.sha256(other.read_bytes()).hexdigest())
        self.catalog.write_text(json.dumps({'documents': [self.doc, doc2]}), encoding='utf-8')
        build_index(self.catalog, self.index, self.root)
        def query(**kwargs):
            return search('الشك المنهجي', self.index, root=self.root, catalog_path=self.catalog, **kwargs)
        self.assertEqual({r['source_id'] for r in query()}, {'drive-test', 'drive-other'})
        self.assertEqual([r['source_id'] for r in query(match='all')], ['drive-test'])
        self.assertEqual([r['source_id'] for r in query(source_id='drive-other')], ['drive-other'])
        self.assertEqual(query(source_id='drive-other', match='all'), [])
        self.assertEqual(query(source_id='drive-test', folder='other'), [])
        with self.assertRaisesRegex(ValueError, 'unknown source ID'):
            query(source_id='missing')
        with self.assertRaisesRegex(ValueError, 'match must'):
            query(match='invalid')

    def test_changed_source_fails_closed(self):
        self.source.write_text(self.text + 'تغيير', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            self.find('الشك')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            build_index(self.catalog, self.index, self.root)

    def test_changed_catalog_requires_rebuild(self):
        self.catalog.write_text(self.catalog.read_text() + ' ', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'catalogue changed'):
            self.find('الشك')

    def test_search_operators_are_data(self):
        self.assertEqual(self.find('"الشك" OR (النفسي)'), self.find('الشك OR النفسي'))
        with self.assertRaisesRegex(ValueError, 'no searchable'):
            self.find('! ()')

    def test_path_outside_import_rejected(self):
        self.doc['path'] = '../outside.txt'
        self.write_catalog()
        with self.assertRaisesRegex(ValueError, 'unsafe or missing'):
            build_index(self.catalog, self.index, self.root)

    def test_chunking_progress_and_full_coverage(self):
        data = '\n'.join(['كلمة ' * 300, 'سطر ثان', 'سطر ثالث', 'سطر رابع'])
        ranges = list(chunks(data, target_words=2, overlap_lines=1))
        self.assertEqual(ranges[0][0], 1)
        self.assertEqual(ranges[-1][1], 4)
        self.assertTrue(all(a[0] < b[0] for a, b in zip(ranges, ranges[1:])))
        self.assertEqual(set(range(1, 5)), {i for start, end, _ in ranges for i in range(start, end + 1)})


if __name__ == '__main__':
    unittest.main()
