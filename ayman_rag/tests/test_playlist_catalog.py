import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'ayman_rag/playlist_inventory.json'
CASES = ROOT / 'ayman_rag/playlist_eval_cases.json'
DRIVE = ROOT / '09_تفريغات_أيمن/drive_inventory.json'
from ayman_rag.build_playlist_catalog import build  # noqa: E402
from ayman_rag.evaluate import evaluate  # noqa: E402
from ayman_rag.search import build_index, read_verified, search  # noqa: E402


class UnifiedPlaylistCatalogTests(unittest.TestCase):
    def test_catalog_rebuilds_and_covers_every_registered_source(self):
        stored = json.loads(CATALOG.read_text(encoding='utf-8'))
        self.assertEqual(stored, build())
        docs = stored['documents']
        self.assertEqual(len(docs), 398)
        self.assertEqual(len({d['id'] for d in docs}), 398)
        self.assertEqual(len({d['path'] for d in docs}), 398)
        playlist_docs = [d for d in docs if d.get('playlist_slug')]
        self.assertEqual(len(playlist_docs), 240)
        self.assertEqual(len(stored['playlists']), 11)
        self.assertEqual(sum(p['episodes'] for p in stored['playlists']), 240)
        drive_paths = {d['path'] for d in json.loads(DRIVE.read_text(encoding='utf-8'))['documents']}
        self.assertTrue(drive_paths <= {d['path'] for d in docs})
        for doc in docs:
            with self.subTest(source=doc['path']):
                self.assertEqual(hashlib.sha256((ROOT / doc['path']).read_bytes()).hexdigest(), doc['sha256'])
                self.assertEqual(doc['speaker_status'], 'unverified')
        decision = [d for d in playlist_docs if d.get('voice') == 'owner-decision']
        self.assertEqual({d['playlist_slug'] for d in decision},
                         {'q100-history', 'rihlat-alyaqeen', 'ayn-al-tariq'})
        self.assertTrue(all(d['owner_gate'] == 'Q1 decided: neutral named guide' for d in decision))
        self.assertTrue(all(d['owner_gate'] == 'approved by owner for publication'
                            for d in playlist_docs if d.get('voice') != 'owner-decision'))

    def test_read_verified_accepts_other_source_roots_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / '01_تفريغات_ومصادر/example/lecture.md'
            source.parent.mkdir(parents=True)
            source.write_text('نص تجريبي', encoding='utf-8')
            doc = {'path': str(source.relative_to(root)),
                   'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
            self.assertEqual(read_verified(doc, root), 'نص تجريبي')
            with self.assertRaisesRegex(ValueError, 'unsafe or missing'):
                read_verified({'path': '../outside.txt', 'sha256': doc['sha256']}, root)

    def test_playlist_filter_and_result_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'transcripts/example'
            folder.mkdir(parents=True)
            docs = []
            for slug, word in (('playlist-a', 'الفكرة الاولى'), ('playlist-b', 'الفكرة الثانية')):
                p = folder / f'{slug}.md'
                p.write_text(word + ' مشتركة\n', encoding='utf-8')
                docs.append({'id': slug, 'path': str(p.relative_to(root)),
                             'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                             'title': slug, 'folder': 'example', 'source_folder_url': '',
                             'playlist_slug': slug, 'episode': 1,
                             'citation_kind': 'paragraph', 'voice': 'ayman',
                             'speaker_status': 'unverified'})
            catalog = root / 'catalog.json'
            index = root / 'index.sqlite3'
            catalog.write_text(json.dumps({'documents': docs}), encoding='utf-8')
            build_index(catalog, index, root)
            results = search('مشتركة', index_path=index, catalog_path=catalog,
                             root=root, playlist_slug='playlist-a', limit=5)
            self.assertTrue(results)
            self.assertTrue(all(r['playlist_slug'] == 'playlist-a' for r in results))
            self.assertEqual(results[0]['episode'], 1)
            self.assertEqual(results[0]['citation_kind'], 'paragraph')
            self.assertEqual(results[0]['voice'], 'ayman')
            self.assertEqual(search('مشتركة', index_path=index, catalog_path=catalog,
                                    root=root, playlist_slug='missing', limit=5), [])

    def test_eleven_known_location_cases_recover_on_the_real_unified_index(self):
        dataset = json.loads(CASES.read_text(encoding='utf-8'))
        self.assertEqual(len(dataset['cases']), 11)
        self.assertEqual({c['playlist_slug'] for c in dataset['cases']},
                         {p['slug'] for p in build()['playlists']})
        by_id = {d['id']: d for d in json.loads(CATALOG.read_text(encoding='utf-8'))['documents']}
        for case in dataset['cases']:
            with self.subTest(case=case['source_id']):
                doc = by_id[case['source_id']]
                lines = (ROOT / doc['path']).read_text(encoding='utf-8').splitlines()
                self.assertIn(case['quote'], lines[case['line'] - 1])
                self.assertEqual(doc['playlist_slug'], case['playlist_slug'])
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / 'playlists.sqlite3'
            build_index(CATALOG, index, ROOT)
            ranks = evaluate(cases_path=CASES, catalog_path=CATALOG, index_path=index)
            self.assertEqual(len(ranks), 11)
            self.assertTrue(all(rank is not None and rank <= dataset['limit'] for rank in ranks))


if __name__ == '__main__':
    unittest.main()
