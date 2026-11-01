#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an optional offline RAG catalogue covering every registered playlist.

The default Drive index remains unchanged. This catalogue adds the timestamped
collections, the paragraph-only PDF-derived collection and the two externally
imported transcript folders, while keeping the 173 Drive files already present
in ``drive_inventory.json``. Duplicate paths are represented once, using the
existing stable Drive ID; every other playlist file gets a path-derived ID.

All metadata is descriptive and unverified. In particular, episode numbers are
the deterministic ones used by ``check_lesson.py``, not recording timestamps and
not necessarily the legacy ``n`` field in ``playlists.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '08_دورات_القوائم' / 'tools'))
from playlist_sources import ROOT as SOURCE_ROOT, citation_kind, header_method, registry, ordered_items  # noqa: E402

DRIVE = ROOT / '09_تفريغات_أيمن' / 'drive_inventory.json'
OUTPUT = ROOT / 'ayman_rag' / 'playlist_inventory.json'
PLAYLIST_CATALOG_SCHEMA = 2

NOTE = (
    'Optional unified offline catalogue: all 173 Drive text files plus one entry for each '
    'file in the ten registered playlists. Paths and SHA-256 are checked against local bytes. '
    'Episode numbers reproduce check_lesson.py file ordering/front matter, not recording time; '
    'the legacy playlists.json n field can differ or repeat. Speaker, recording, edition, '
    'timestamps, transcription method and factual accuracy remain unverified. Non-Ayman '
    'playlists are kept separate and are not written in Ayman voice. No official course map '
    'is approved by this catalogue.'
)


def _base_doc(path: str, sha: str, item: dict, playlist: dict):
    source = (SOURCE_ROOT / path).resolve()
    kind = citation_kind(path)
    timestamps = ('present_unverified' if kind == 'timestamp'
                  else 'not_applicable_line' if kind == 'line' else 'none_detected')
    return {
        'id': 'playlist-' + hashlib.sha256(path.encode('utf-8')).hexdigest()[:20],
        'path': path,
        'sha256': sha,
        'title': item['title'],
        'folder': source.parent.name,
        'source_folder_url': '',
        'speaker_status': 'unverified',
        'speaker': playlist.get('speaker'),
        'edition': None,
        'transcription_method': header_method(path),
        'original_media_url': item.get('url'),
        'timestamps': timestamps,
        'line_count': len(source.read_text(encoding='utf-8', errors='replace').splitlines()),
        'word_count': item.get('words'),
        'playlist_slug': playlist['slug'],
        'playlist_title': playlist['title'],
        'playlist_phase': playlist.get('phase'),
        'playlist_voice': playlist.get('voice'),
        'voice': playlist.get('voice'),
        'atlas': bool(playlist.get('atlas')),
        'episode': item['episode'],
        'registry_episode': item['registry_episode'],
        'registry_sha': item.get('sha'),
        'citation': playlist.get('citation'),
        'citation_kind': kind,
        'course_dir': playlist.get('course_dir'),
        'owner_gate': 'Q1 pending' if playlist.get('voice') == 'owner-decision' else 'draft; owner approval pending',
    }


def build(root: Path = ROOT, drive_path: Path = DRIVE) -> dict:
    drive = json.loads(drive_path.read_text(encoding='utf-8'))['documents']
    by_path = {d['path']: d for d in drive}
    if len(by_path) != len(drive):
        raise ValueError('duplicate paths in Drive inventory')
    docs, seen_paths, ids = [], set(), set()
    playlists = registry()['playlists']
    for playlist in playlists:
        for item in ordered_items(playlist):
            path = item['path']
            source = root / path
            if not source.is_file():
                raise ValueError(f'missing playlist source: {path}')
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            if path in by_path:
                base = dict(by_path[path])
                if base['sha256'] != sha:
                    raise ValueError(f'Drive/playlist SHA-256 mismatch: {path}')
            else:
                base = _base_doc(path, sha, item, playlist)
            base.update({
                'playlist_slug': playlist['slug'],
                'playlist_title': playlist['title'],
                'playlist_phase': playlist.get('phase'),
                'playlist_voice': playlist.get('voice'),
                'voice': playlist.get('voice'),
                'atlas': bool(playlist.get('atlas')),
                'episode': item['episode'],
                'registry_episode': item['registry_episode'],
                'registry_sha': item.get('sha'),
                'citation': playlist.get('citation'),
                'citation_kind': citation_kind(path),
                'course_dir': playlist.get('course_dir'),
                'owner_gate': 'Q1 pending' if playlist.get('voice') == 'owner-decision' else 'draft; owner approval pending',
                'speaker': playlist.get('speaker'),
                'speaker_status': 'unverified',
                'original_media_url': base.get('original_media_url') or item.get('url'),
                'transcription_method': base.get('transcription_method') or header_method(path),
                'timestamps': base.get('timestamps') or ('present_unverified' if citation_kind(path) == 'timestamp' else None),
            })
            if path in seen_paths or base['id'] in ids:
                raise ValueError(f'duplicate catalogue source: {path}')
            seen_paths.add(path)
            ids.add(base['id'])
            docs.append(base)
    # Keep the remaining Drive files searchable too, with explicit defaults.
    for doc in drive:
        if doc['path'] in seen_paths:
            continue
        base = dict(doc)
        base.setdefault('playlist_slug', '')
        base.setdefault('episode', 0)
        base.setdefault('registry_episode', None)
        base.setdefault('registry_sha', None)
        base.setdefault('playlist_title', '')
        base.setdefault('playlist_phase', None)
        base.setdefault('playlist_voice', '')
        base.setdefault('voice', '')
        base.setdefault('atlas', False)
        base.setdefault('citation', 'line')
        base.setdefault('citation_kind', 'line')
        base.setdefault('course_dir', '')
        base.setdefault('owner_gate', 'draft; owner approval pending')
        base.setdefault('speaker', 'منسوب في أسماء الملفات؛ المتحدث لم يتحقق')
        base.setdefault('speaker_status', 'unverified')
        base.setdefault('source_folder_url', '')
        base.setdefault('transcription_method', None)
        base.setdefault('original_media_url', None)
        base.setdefault('timestamps', None)
        if base['path'] in seen_paths or base['id'] in ids:
            raise ValueError(f'duplicate catalogue source: {base["path"]}')
        seen_paths.add(base['path'])
        ids.add(base['id'])
        docs.append(base)
    docs.sort(key=lambda d: (d.get('playlist_slug', ''), d.get('episode', 0), d['path']))
    summary = [{'slug': p['slug'], 'title': p['title'], 'episodes': len(ordered_items(p)),
                'voice': p.get('voice'), 'citation': p.get('citation'),
                'warnings': p.get('warnings', [])} for p in playlists]
    return {'schema_version': PLAYLIST_CATALOG_SCHEMA, 'note': NOTE,
            'playlists': summary, 'documents': docs}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare without writing')
    args = parser.parse_args(argv)
    result = build()
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    current = OUTPUT.read_text(encoding='utf-8') if OUTPUT.exists() else None
    if args.check:
        if current != text:
            print('✗ unified playlist catalogue needs regeneration')
            return 1
        print(f'ok: {len(result["documents"])} sources in the unified catalogue match local bytes')
        return 0
    if current != text:
        OUTPUT.write_text(text, encoding='utf-8')
    print(f'Wrote {len(result["documents"])} sources to {OUTPUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
