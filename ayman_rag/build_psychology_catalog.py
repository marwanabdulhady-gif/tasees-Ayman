#!/usr/bin/env python3
"""Build a local psychology-only catalogue from Drive and existing transcripts.

Original files remain unchanged. Legacy hashes describe current repository
bytes; they do not independently verify the recording or transcription.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = ROOT / '09_تفريغات_أيمن/drive_inventory.json'
LEGACY = ROOT / 'transcripts/03-psychology'
OUTPUT = ROOT / 'ayman_rag/psychology_inventory.json'
DRIVE_FOLDER = 'دورة-علم-النفس-م-أيمن-عبد-الرحيم'


def build(root=ROOT, drive_path=DRIVE):
    drive_docs = [d for d in json.loads(drive_path.read_text(encoding='utf-8'))['documents']
                  if d['folder'] == DRIVE_FOLDER]
    if len(drive_docs) != 11:
        raise ValueError('expected 11 Drive psychology sources; review the catalogue')
    allowed_drive = (root / 'transcripts/drive-import-2026-11-01').resolve()
    for doc in drive_docs:
        path = (root / doc['path']).resolve()
        if not path.is_relative_to(allowed_drive) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != doc['sha256']:
            raise ValueError(f"Drive source missing, unsafe or changed: {doc['path']}")
    folder = root / 'transcripts/03-psychology'
    files = sorted(folder.glob('[0-9][0-9] *.md'))
    numbers = [int(p.name[:2]) for p in files]
    if numbers != list(range(1, 11)):
        raise ValueError('expected exactly numbered legacy psychology episodes 01–10')
    docs = []
    for p in files:
        resolved = p.resolve()
        if not resolved.is_relative_to(folder.resolve()) or not resolved.is_file():
            raise ValueError(f'unsafe legacy source: {p}')
        data = resolved.read_bytes()
        text = data.decode('utf-8')
        path = str(resolved.relative_to(root.resolve()))
        # The video link and transcription method are metadata recorded in the
        # existing file, not independently verified provenance or timing.
        header = '\n'.join(text.splitlines()[:8])
        urls = re.findall(r'https://www\.youtube\.com/watch\?v=[\w-]+', header)
        if len(urls) != 1:
            raise ValueError(f'expected one header recording link: {p.name}')
        docs.append({'id': 'legacy-psy-' + hashlib.sha256(path.encode('utf-8')).hexdigest()[:20],
                     'path': path, 'sha256': hashlib.sha256(data).hexdigest(),
                     'title': p.stem, 'folder': '03-psychology', 'source_folder_url': '',
                     'speaker_status': 'unverified', 'edition': None,
                     'transcription_method': 'Supadata API (claimed in file header)',
                     'original_media_url': urls[0], 'timestamps': 'present_unverified',
                     'line_count': len(text.splitlines()), 'word_count': len(text.split())})
    combined = drive_docs + docs
    if len({d['id'] for d in combined}) != len(combined) or len({d['path'] for d in combined}) != len(combined):
        raise ValueError('duplicate source IDs or paths')
    return {'schema_version': 1, 'note': '11 Drive text files and 10 existing timestamped Markdown files. Recording links and transcription methods are file-header claims, not independently verified. Similar transcripts are retained as separate editions; timestamps are unverified.',
            'documents': combined}


def main():
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Wrote {len(result['documents'])} psychology sources to {OUTPUT.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
