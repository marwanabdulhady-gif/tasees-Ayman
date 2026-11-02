# -*- coding: utf-8 -*-
"""The review queue must stay explicit, complete and strictly unapproved."""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELF = ROOT / '08_دورات_القوائم' / '10_مسودات_القوائم'
REPORT = SHELF / '00_طابور_المراجعة.json'
BOARD = SHELF / '03_لوحة_المراجعة' / 'index.html'
CATALOG = ROOT / 'ayman_rag' / 'playlist_inventory.json'


class ReviewQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text(encoding='utf-8'))
        cls.catalog = {d['path']: d for d in json.loads(CATALOG.read_text(encoding='utf-8'))['documents']}

    def test_totals_and_explicit_gates(self):
        r = self.report
        self.assertEqual(r['status'], 'طابور مراجعة مفتوح؛ لا بند معتمد')
        self.assertEqual(r['totals'], {
            'playlists': 10, 'sources': 225, 'lessons': 94, 'screens': 940,
            'pending_source_reviews': 225, 'pending_lesson_reviews': 94,
            'blocked_publications': 94,
        })
        self.assertEqual(set(r['gates']['owner_q1']['playlists']),
                         {'q100-history', 'rihlat-alyaqeen'})
        self.assertEqual(r['gates']['publication']['status'], 'blocked')
        for gate in ('official_map_approval', 'audio_and_speaker',
                     'references_and_safety', 'owner_content_approval'):
            self.assertEqual(r['gates'][gate]['status'], 'pending')
        dimensions = {d['id']: d for d in r['review_dimensions']}
        self.assertEqual(dimensions['publication']['status'], 'blocked')
        self.assertEqual(dimensions['local_bytes_and_citation_positions']['status'],
                         'verified_local_only')
        self.assertTrue(dimensions['local_bytes_and_citation_positions']['automated'])

    def test_every_source_and_lesson_is_covered_and_unapproved(self):
        entries = self.report['playlists']
        self.assertEqual(len(entries), 10)
        sources = [s for e in entries for s in e['sources']]
        lessons = [l for e in entries for l in e['lessons']]
        self.assertEqual(len(sources), 225)
        self.assertEqual(len(lessons), 94)
        self.assertEqual(len({s['path'] for s in sources}), 225)
        self.assertEqual(len({l['text'] for l in lessons}), 94)
        for s in sources:
            with self.subTest(source=s['path']):
                doc = self.catalog[s['path']]
                self.assertEqual(s['sha256'], doc['sha256'])
                self.assertEqual(s['catalog_id'], doc['id'])
                self.assertTrue(s['registry_sha_prefix_ok'])
                self.assertEqual(s['review_status']['publication'], 'blocked')
                self.assertEqual(s['review_status']['owner_approval'], 'pending')
                self.assertEqual(s['review_status']['audio_recording'], 'pending')
                self.assertIsNone(s['review_status']['decision'])
                self.assertIn('speaker_status_unverified', s['flags'])
        for l in lessons:
            with self.subTest(lesson=l['text']):
                self.assertTrue((SHELF / l['text']).is_file())
                self.assertTrue((SHELF / l['screen']).is_file())
                self.assertEqual(hashlib.sha256((SHELF / l['text']).read_bytes()).hexdigest(),
                                 l['text_sha256'])
                self.assertEqual(hashlib.sha256((SHELF / l['screen']).read_bytes()).hexdigest(),
                                 l['screen_sha256'])
                self.assertEqual(l['citation_count'], 6)
                self.assertTrue(l['source_ids'])
                self.assertEqual(l['review_status']['publication'], 'blocked')
                self.assertEqual(l['review_status']['owner_approval'], 'pending')
                self.assertEqual(l['review_status']['content_accuracy'], 'pending')

    def test_required_reviews_and_registry_integrity_flags(self):
        by_slug = {e['slug']: e for e in self.report['playlists']}
        self.assertIn('owner_q1_decision', by_slug['q100-history']['required_reviews'])
        self.assertIn('owner_q1_decision', by_slug['rihlat-alyaqeen']['required_reviews'])
        self.assertIn('clinical_safety_review', by_slug['ayman-psychology']['required_reviews'])
        self.assertIn('scientific_reference_review', by_slug['rihlat-alyaqeen']['required_reviews'])
        self.assertIn('historical_sensitivity_review', by_slug['q100-history']['required_reviews'])
        self.assertIn('prophet_and_companions_respect_review',
                      by_slug['ayman-seerah-makkah']['required_reviews'])
        integrity = self.report['registry_integrity']
        self.assertEqual([x['slug'] for x in integrity['duplicate_registry_episode_playlists']],
                         ['ayman-tasees'])
        self.assertEqual(integrity['duplicate_registry_episode_playlists'][0]['episodes'], [16])
        self.assertEqual(integrity['registry_sha_prefix_mismatch_count'], 0)
        self.assertEqual(integrity['episode_order_mismatch_count'], 1)
        self.assertEqual(by_slug['ayman-tasees']['registry_integrity']['duplicate_registry_episodes'],
                         [16])

    def test_generated_markdown_and_dashboard_links_resolve(self):
        self.assertTrue((SHELF / '00_طابور_المراجعة.md').is_file())
        for e in self.report['playlists']:
            queue = SHELF / e['slug'] / '00_طابور_المراجعة.md'
            with self.subTest(queue=str(queue.relative_to(ROOT))):
                text = queue.read_text(encoding='utf-8')
                self.assertTrue(queue.is_file())
                self.assertIn('pending / blocked', text)
                self.assertIn('الطابور الجذري', text)
        html = BOARD.read_text(encoding='utf-8')
        self.assertIn('لا بند معتمد', html)
        self.assertIn('tasees-tokens.css', html)
        for rel in re.findall(r'(?:href|src)="([^"]+)"', html):
            if rel.startswith('#'):
                continue
            target = (BOARD.parent / rel).resolve()
            self.assertTrue(target.exists(), f'dashboard broken link: {rel}')
        self.assertIn('playlist_retrieval_audit.md', html)


if __name__ == '__main__':
    unittest.main()
