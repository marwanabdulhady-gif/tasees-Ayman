#!/usr/bin/env python3
"""Offline, evidence-first search over the imported Ayman transcript collection.

This is retrieval only: no LLM, model downloads, external requests, or generated
answers. Build the SQLite FTS index locally; cited text always comes from source.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / '09_تفريغات_أيمن/drive_inventory.json'
INDEX = ROOT / '.cache/ayman-rag/index.sqlite3'
IMPORT = ROOT / 'transcripts/drive-import-2026-11-01'
WORD = re.compile(r'[\w]+', re.UNICODE)


def normalize(text):
    text = unicodedata.normalize('NFKC', text).lower()
    text = ''.join(c for c in text if not unicodedata.combining(c) and c != '\u0640')
    return text.translate(str.maketrans({'أ':'ا', 'إ':'ا', 'آ':'ا', 'ٱ':'ا', 'ى':'ي', 'ة':'ه'}))


def chunks(text, target_words=180, overlap_lines=1):
    """Yield 1-based inclusive line ranges, always progressing even on long lines."""
    lines = text.splitlines(keepends=True)
    start = 0
    while start < len(lines):
        end, count = start, 0
        while end < len(lines) and (count < target_words or end == start):
            count += len(lines[end].split())
            end += 1
        excerpt = ''.join(lines[start:end])
        if excerpt.strip():
            yield start + 1, end, excerpt
        if end == len(lines):
            break
        start = max(start + 1, end - overlap_lines)


def read_verified(doc, root=ROOT):
    path = (root / doc['path']).resolve()
    allowed = (root / 'transcripts/drive-import-2026-11-01').resolve()
    if not path.is_relative_to(allowed) or not path.is_file():
        raise ValueError(f"unsafe or missing source path: {doc['path']}")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != doc['sha256']:
        raise ValueError(f"source changed; rebuild inventory and index after reviewing: {doc['path']}")
    return data.decode('utf-8')


def build_index(catalog_path=CATALOG, index_path=INDEX, root=ROOT):
    payload = json.loads(catalog_path.read_text(encoding='utf-8'))
    docs = payload['documents']
    if not docs or len({d['id'] for d in docs}) != len(docs):
        raise ValueError('empty catalogue or duplicate source IDs')
    # Verify everything before replacing the previous index.
    verified = [(d, read_verified(d, root)) for d in docs]
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = index_path.with_suffix(index_path.suffix + '.tmp')
    if tmp.exists():
        tmp.unlink()
    try:
        with sqlite3.connect(tmp) as db:
            db.executescript('''CREATE TABLE sources (id TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, title TEXT NOT NULL, folder TEXT NOT NULL, folder_url TEXT NOT NULL);
              CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_id TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL);
              CREATE VIRTUAL TABLE passage_search USING fts5(text, chunk_id UNINDEXED, tokenize="unicode61");
              CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);''')
            count = 0
            for doc, text in verified:
                db.execute('INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)', (doc['id'], doc['path'], doc['sha256'], doc['title'], doc['folder'], doc['source_folder_url']))
                for start, end, passage in chunks(text):
                    cur = db.execute('INSERT INTO chunks(source_id,start_line,end_line) VALUES (?,?,?)', (doc['id'], start, end))
                    db.execute('INSERT INTO passage_search(text,chunk_id) VALUES (?,?)', (normalize(passage), cur.lastrowid))
                    count += 1
            db.execute('INSERT INTO metadata VALUES (?,?)', ('catalog_sha256', hashlib.sha256(catalog_path.read_bytes()).hexdigest()))
        tmp.replace(index_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return len(docs), count


def search(query, index_path=INDEX, limit=5, root=ROOT, catalog_path=CATALOG, folder=None,
           source_id=None, match='any'):
    tokens = list(dict.fromkeys(WORD.findall(normalize(query))))[:20]
    if not tokens:
        raise ValueError('query contains no searchable terms')
    if not 1 <= limit <= 50:
        raise ValueError('limit must be between 1 and 50')
    if match not in ('any', 'all'):
        raise ValueError('match must be any or all')
    if not index_path.is_file():
        raise ValueError('index missing: run build first')
    # Quote tokens so FTS operators and punctuation cannot change the query.
    expression = (' OR ' if match == 'any' else ' AND ').join('"' + t.replace('"', '""') + '"' for t in tokens)
    uri = index_path.resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        saved = db.execute("SELECT value FROM metadata WHERE key='catalog_sha256'").fetchone()
        if not saved or saved[0] != hashlib.sha256(catalog_path.read_bytes()).hexdigest():
            raise ValueError('catalogue changed; rebuild the index')
        if source_id is not None and not db.execute('SELECT 1 FROM sources WHERE id = ?', (source_id,)).fetchone():
            raise ValueError('unknown source ID')
        rows = db.execute('''SELECT s.id, s.path, s.sha256, s.title, s.folder, s.folder_url,
                   c.start_line, c.end_line, bm25(passage_search) AS rank
            FROM passage_search JOIN chunks c ON c.id = passage_search.chunk_id
            JOIN sources s ON s.id = c.source_id
            WHERE passage_search MATCH ? AND (? IS NULL OR s.folder = ?)
              AND (? IS NULL OR s.id = ?)
            ORDER BY rank, c.id LIMIT ?''', (expression, folder, folder, source_id, source_id, limit)).fetchall()
    results, verified = [], {}
    for id_, path, sha, title, folder, folder_url, start, end, rank in rows:
        if id_ not in verified:
            verified[id_] = read_verified({'path': path, 'sha256': sha}, root).splitlines(keepends=True)
        lines = verified[id_]
        if start < 1 or end < start or end > len(lines):
            raise ValueError(f'invalid source span for {path}; rebuild index')
        results.append({'source_id': id_, 'title': title, 'folder': folder, 'path': path,
                        'sha256': sha, 'start_line': start, 'end_line': end,
                        'source_folder_url': folder_url, 'speaker_status': 'unverified',
                        'excerpt': ''.join(lines[start-1:end]).strip(), 'score': rank})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build')
    p = sub.add_parser('search'); p.add_argument('query'); p.add_argument('--limit', type=int, default=5); p.add_argument('--folder', help='exact folder name from the inventory'); p.add_argument('--source-id', help='exact source ID from the inventory'); p.add_argument('--match', choices=('any', 'all'), default='any', help='match any token (default) or all tokens in one passage'); p.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'build':
            docs, count = build_index(); print(f'Indexed {docs} sources and {count} passages locally in {INDEX.relative_to(ROOT)}')
        else:
            results = search(args.query, limit=args.limit, folder=args.folder, source_id=args.source_id, match=args.match)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            elif not results:
                print('No matching passages. Try different terms.')
            else:
                for i, r in enumerate(results, 1):
                    print(f"\n[{i}] {r['title']} — lines {r['start_line']}–{r['end_line']}\nSource ID: {r['source_id']}\n{r['path']}\nSource SHA-256: {r['sha256']}\n{r['excerpt']}\n")
    except (ValueError, OSError, sqlite3.Error, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f'error: {exc}\n')


if __name__ == '__main__':
    main()
