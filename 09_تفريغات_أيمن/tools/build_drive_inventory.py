#!/usr/bin/env python3
"""Build a deterministic inventory of the unmodified Drive transcript import.

No network access. SHA256SUMS is the import-time manifest, not an independent
attestation of speaker, completeness, edition, or transcription quality.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
IMPORT = ROOT / 'transcripts/drive-import-2026-11-01'
OUTPUT = ROOT / '09_تفريغات_أيمن/drive_inventory.json'
FOLDER = 'https://drive.google.com/drive/folders/1Fr3Lg8QCyjMWbG2B9KDg6WhKC134gz7E'


def build():
    links = {}
    for encoded, url in re.findall(r'\| \[[^\]]+\]\(([^)]+)/\) \| \d+ \| \[Drive\]\((https://drive\.google\.com/drive/folders/[\w-]+)\) \|', (IMPORT / 'README.md').read_text(encoding='utf-8')):
        links[unquote(encoded)] = url
    expected = {}
    for line in (IMPORT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest, rel = line.split('  ', 1)
        if not re.fullmatch(r'[0-9a-f]{64}', digest) or rel in expected:
            raise ValueError(f'invalid or duplicate checksum entry: {rel}')
        expected[rel] = digest
    found = {str(p.relative_to(IMPORT)) for p in IMPORT.rglob('*.txt')}
    if found != set(expected):
        raise ValueError(f'checksum inventory mismatch: missing={set(expected)-found}, extra={found-set(expected)}')
    docs = []
    for rel in sorted(expected):
        p = (IMPORT / rel).resolve()
        if not p.is_relative_to(IMPORT.resolve()) or not p.is_file():
            raise ValueError(f'unsafe path: {rel}')
        data = p.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        if sha != expected[rel]:
            raise ValueError(f'checksum mismatch: {rel}')
        text = data.decode('utf-8')
        folder = Path(rel).parts[0]
        if folder not in links:
            raise ValueError(f'missing folder link: {folder}')
        path = str(p.relative_to(ROOT))
        docs.append({'id': 'drive-' + hashlib.sha256(path.encode()).hexdigest()[:20],
                     'path': path, 'sha256': sha, 'title': p.stem,
                     'folder': folder, 'source_folder_url': links[folder],
                     'speaker_status': 'unverified', 'edition': None,
                     'transcription_method': None, 'original_media_url': None,
                     'timestamps': None, 'line_count': len(text.splitlines()),
                     'word_count': len(text.split())})
    if len({d['id'] for d in docs}) != len(docs):
        raise ValueError('source ID collision')
    return {'schema_version': 1, 'source_folder_url': FOLDER,
            'note': 'Speaker, edition, transcription method, completeness, and accuracy are not verified; folder links are not original recording links.',
            'documents': docs}


def main():
    payload = build()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Wrote {len(payload['documents'])} checksum-verified sources to {OUTPUT.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
