#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic plumbing audit for the optional unified playlist RAG index.

    python3 ayman_rag/audit_playlist_retrieval.py
    python3 ayman_rag/audit_playlist_retrieval.py --check
    python3 ayman_rag/audit_playlist_retrieval.py --index .cache/ayman-rag/playlists.sqlite3

This checks local bytes, catalogue counts, exact ``--playlist`` isolation,
cross-playlist leakage, unknown-slug/negative controls and the eleven existing
known-location lexical probes. It does **not** measure semantic relevance,
answer correctness, recording/speaker accuracy, references or owner approval.
The default Drive index is unchanged; a temporary unified index is built when
``--index`` is omitted.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '08_دورات_القوائم' / 'tools'))
from ayman_rag.evaluate import evaluate, target_rank  # noqa: E402
from ayman_rag.search import ROOT as SEARCH_ROOT, build_index, read_verified, search  # noqa: E402
from playlist_sources import ordered_items, registry  # noqa: E402
from owner_decisions import APPROVED_GATE, Q1_GATE  # noqa: E402

CATALOG = ROOT / 'ayman_rag' / 'playlist_inventory.json'
CASES = ROOT / 'ayman_rag' / 'playlist_eval_cases.json'
OUTPUT_JSON = ROOT / 'ayman_rag' / 'playlist_retrieval_audit.json'
OUTPUT_MD = ROOT / 'ayman_rag' / 'playlist_retrieval_audit.md'
NEGATIVE_QUERY = 'قطرسونيك'
UNKNOWN_SLUG = 'playlist-slug-that-does-not-exist'

NOTE = (
    'Deterministic plumbing audit of the optional unified offline playlist index. '
    'PASS means local bytes, catalogue metadata, exact playlist filters and the '
    'selected known-location probes behaved as expected. The owner has recorded a '
    'final approval and a neutral-named-guide Q1 decision; this audit is not '
    'semantic relevance, answer correctness, medical/scientific accuracy, '
    'recording or speaker verification, independent reference review, or '
    'automated proof of that administrative decision.'
)
LIMITS = [
    'FTS5/BM25 retrieval is lexical, not semantic; the eleven probes echo their source wording.',
    'Other retrieved passages are unjudged; a hit does not prove the passage answers a question.',
    'Exact --playlist isolation is a metadata/plumbing check, not proof of attribution or content truth.',
    'The owner approval is administrative; audio, speaker, edition, transcription, independent references, clinical/scientific/historical review and external publication are not automatically established.',
    'The default Drive index and the psychology-only index are unchanged; this report concerns the optional unified index.',
]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _catalog_checks(catalog_path: Path):
    data = json.loads(catalog_path.read_text(encoding='utf-8'))
    docs = data['documents']
    by_id = {d['id']: d for d in docs}
    by_path = {d['path']: d for d in docs}
    _require(len(docs) == len(by_id) == len(by_path) == 398,
             f'expected 398 unique catalogue documents, got {len(docs)}')
    for doc in docs:
        path = ROOT / doc['path']
        _require(path.is_file(), f'missing source: {doc["path"]}')
        _require(hashlib.sha256(path.read_bytes()).hexdigest() == doc['sha256'],
                 f'SHA-256 mismatch: {doc["path"]}')
        _require(doc.get('speaker_status') == 'unverified',
                 f'unexpected speaker status: {doc["path"]}')
    counts = Counter(d.get('playlist_slug', '') for d in docs)
    expected = {p['slug']: len(ordered_items(p)) for p in registry()['playlists']}
    for slug, count in expected.items():
        _require(counts[slug] == count, f'{slug}: expected {count} sources, got {counts[slug]}')
    _require(sum(expected.values()) == 240, 'registry playlist sources must total 240')
    _require(len(expected) == 11, 'expected eleven registered playlists')
    _require(counts[''] == 158, f'expected 158 unassigned Drive sources, got {counts[""]}')
    decision = [d for d in docs if d.get('voice') == 'owner-decision']
    _require({d['playlist_slug'] for d in decision} ==
             {'q100-history', 'rihlat-alyaqeen', 'ayn-al-tariq'},
             'owner-decision voice policy changed')
    _require(all(d['owner_gate'] == Q1_GATE for d in decision),
             'Q1 gate missing from owner-decision sources')
    _require(all(d['owner_gate'] == APPROVED_GATE for d in docs
                 if d.get('voice') != 'owner-decision'),
             'owner approval gate missing from non-decision sources')
    return {
        'catalog_sha256': hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        'documents': len(docs),
        'playlist_sources': sum(expected.values()),
        'unassigned_drive_sources': counts[''],
        'playlists': len(expected),
        'source_bytes_verified': len(docs),
        'owner_decision_sources': len(decision),
    }


def _search_checks(catalog_path: Path, cases_path: Path, index_path: Path):
    dataset = json.loads(cases_path.read_text(encoding='utf-8'))
    cases = dataset['cases']
    limit = dataset['limit']
    slugs = [c['playlist_slug'] for c in cases]
    _require(len(cases) == 11 and len(set(slugs)) == 11,
             'expected one known-location case for each of the eleven playlists')
    catalog_docs = {d['id']: d for d in json.loads(catalog_path.read_text(encoding='utf-8'))['documents']}

    filter_rows, leak_rows = [], []
    for i, case in enumerate(cases):
        slug = case['playlist_slug']
        other_slug = slugs[(i + 1) % len(slugs)]
        _require(case['source_id'] in catalog_docs, f'unknown case source: {case["source_id"]}')
        _require(catalog_docs[case['source_id']]['playlist_slug'] == slug,
                 f'case {slug}: source belongs to another playlist')
        lines = read_verified(catalog_docs[case['source_id']], SEARCH_ROOT).splitlines()
        _require(1 <= case['line'] <= len(lines) and case['quote'] in lines[case['line'] - 1],
                 f'case {slug}: quote/line invalid')

        filtered = search(case['query'], index_path=index_path, catalog_path=catalog_path,
                          root=SEARCH_ROOT, playlist_slug=slug, limit=limit)
        rank = target_rank(filtered, case)
        all_in_slug = all(r['playlist_slug'] == slug for r in filtered)
        _require(filtered and all_in_slug and rank is not None,
                 f'case {slug}: exact playlist filter failed or target missing')
        filter_rows.append({'playlist_slug': slug, 'source_id': case['source_id'],
                            'filtered_rank': rank, 'filtered_results': len(filtered),
                            'all_results_in_requested_playlist': all_in_slug})

        other = search(case['query'], index_path=index_path, catalog_path=catalog_path,
                       root=SEARCH_ROOT, playlist_slug=other_slug, limit=limit)
        absent = case['source_id'] not in {r['source_id'] for r in other}
        other_ok = all(r['playlist_slug'] == other_slug for r in other)
        _require(absent and other_ok,
                 f'case {slug}: source leaked through {other_slug} filter')
        leak_rows.append({'playlist_slug': slug, 'other_playlist_slug': other_slug,
                          'other_results': len(other), 'expected_source_absent': absent,
                          'all_other_results_in_other_playlist': other_ok})

    unknown = search(cases[0]['query'], index_path=index_path, catalog_path=catalog_path,
                     root=SEARCH_ROOT, playlist_slug=UNKNOWN_SLUG, limit=limit)
    _require(unknown == [], 'unknown playlist slug returned results')
    negative = search(NEGATIVE_QUERY, index_path=index_path, catalog_path=catalog_path,
                      root=SEARCH_ROOT, limit=limit)
    _require(negative == [], 'negative-control query returned results')

    with contextlib.redirect_stdout(io.StringIO()):
        ranks = evaluate(cases_path=cases_path, match='any',
                         catalog_path=catalog_path, index_path=index_path)
    hits = sum(r is not None and r <= limit for r in ranks)
    _require(hits == len(cases), f'known-location hits fell below {len(cases)}/{len(cases)}')
    return {
        'known_location': {'hits': hits, 'total': len(cases), 'limit': limit,
                           'unfiltered_ranks': ranks},
        'filter_isolation': filter_rows,
        'cross_playlist_leakage': leak_rows,
        'unknown_playlist_slug': {'slug': UNKNOWN_SLUG, 'results': len(unknown)},
        'negative_control': {'query': NEGATIVE_QUERY, 'results': len(negative)},
    }


def build(catalog_path=CATALOG, cases_path=CASES, index_path=None):
    """Return (report_dict, markdown). Build a temporary index unless one is given."""
    catalog_info = _catalog_checks(catalog_path)
    if index_path is None:
        with tempfile.TemporaryDirectory(prefix='playlist-audit-') as tmp:
            temp_index = Path(tmp) / 'playlists.sqlite3'
            build_index(catalog_path, temp_index, SEARCH_ROOT)
            search_info = _search_checks(catalog_path, cases_path, temp_index)
    else:
        search_info = _search_checks(catalog_path, cases_path, Path(index_path))
    checks = [
        {'id': 'catalog_bytes_and_counts', 'status': 'pass',
         'detail': f'{catalog_info["documents"]} checksum-verified sources; '
                   f'{catalog_info["playlist_sources"]} playlist sources; '
                   f'{catalog_info["unassigned_drive_sources"]} unassigned Drive sources.'},
        {'id': 'filter_isolation', 'status': 'pass',
         'detail': 'Each of the eleven probes returns only its requested playlist and its target source.'},
        {'id': 'cross_playlist_leakage', 'status': 'pass',
         'detail': 'No target source appears when its query is filtered to a different playlist.'},
        {'id': 'unknown_playlist_slug', 'status': 'pass',
         'detail': 'An unknown exact slug returns zero results.'},
        {'id': 'negative_control', 'status': 'pass',
         'detail': 'A nonsense lexical query returns zero results.'},
        {'id': 'known_location_hits', 'status': 'pass',
         'detail': f'{search_info["known_location"]["hits"]}/'
                   f'{search_info["known_location"]["total"]} selected locations in the top '
                   f'{search_info["known_location"]["limit"]}.'},
    ]
    report = {
        'schema_version': 2,
        'status': 'pass',
        'note': NOTE,
        'catalog': catalog_info,
        'checks': checks,
        'results': search_info,
        'limits': LIMITS,
    }
    md = _markdown(report)
    return report, md


def _markdown(report):
    r = report['results']
    lines = [
        '# تدقيق استرجاع القوائم الإحدى عشرة — فحص بنيوي',
        '',
        '> **PASS هنا فحص بنيوي فقط.** يثبت مطابقة البايتات المحلية، وعدد المصادر، وعزل '
        '`--playlist`، وأحد عشر موضعًا معروفًا مختارًا. لا يثبت دلالة، ولا صحة إجابة، ولا '
        'التسجيل، ولا المتحدث، ولا المراجع، ولا المراجعات المتخصصة. قرار المالك بالاعتماد '
        'موثق في `00_قرارات_المالك.json`، لكن هذا التدقيق لا يثبته آليًا.',
        '',
        f'- المصادر: **{report["catalog"]["documents"]}**، منها '
        f'**{report["catalog"]["playlist_sources"]}** للقوائم الإحدى عشرة و'
        f'**{report["catalog"]["unassigned_drive_sources"]}** ملف Drive غير منسوب.',
        f'- بصمة الكتالوج: `{report["catalog"]["catalog_sha256"]}`',
        f'- المواضع المعروفة: **{r["known_location"]["hits"]}/'
        f'{r["known_location"]["total"]}** ضمن أول {r["known_location"]["limit"]} نتائج.',
        '',
        '## الفحوص',
        '',
        '| الفحص | النتيجة | التفصيل |',
        '|---|---|---|',
    ]
    for c in report['checks']:
        lines.append(f'| `{c["id"]}` | {c["status"]} | {c["detail"]} |')
    lines += ['', '## عزل كل قائمة', '',
              '| القائمة | رتبة الهدف تحت الفلتر | نتائج الفلتر | قائمة أخرى فُحصت | تسريب الهدف |',
              '|---|---:|---:|---|---|']
    leak = {x['playlist_slug']: x for x in r['cross_playlist_leakage']}
    for f in r['filter_isolation']:
        l = leak[f['playlist_slug']]
        lines.append(f'| `{f["playlist_slug"]}` | {f["filtered_rank"]} | '
                     f'{f["filtered_results"]} | `{l["other_playlist_slug"]}` | '
                     f'{"لا" if l["expected_source_absent"] else "نعم"} |')
    lines += ['', '## حدود صارمة', '']
    lines += [f'- {x}' for x in report['limits']]
    lines += ['', 'الأوامر والتفاصيل في [`README.md`](README.md). '
              'البيانات الكاملة في [`playlist_retrieval_audit.json`](playlist_retrieval_audit.json).', '']
    return '\n'.join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare without writing')
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--cases', type=Path, default=CASES)
    parser.add_argument('--index', type=Path, default=None,
                        help='use an existing unified index; otherwise build a temporary one')
    args = parser.parse_args(argv)
    try:
        report, md = build(args.catalog, args.cases, args.index)
    except (OSError, ValueError, KeyError) as exc:
        print(f'error: {exc}')
        return 1
    generated = {OUTPUT_JSON: json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                 OUTPUT_MD: md}
    changed = [str(p.relative_to(ROOT)) for p, text in generated.items()
               if not p.exists() or p.read_text(encoding='utf-8') != text]
    if args.check:
        if changed:
            print('✗ تقرير تدقيق الاسترجاع يحتاج إعادة توليد:')
            for path in changed:
                print('  ' + path)
            return 1
        print('ok: تقرير تدقيق الاسترجاع مطابق للكتالوج والفهرس الموحد')
        return 0
    for p, text in generated.items():
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} audit files; status=pass, '
          f'{report["results"]["known_location"]["hits"]}/'
          f'{report["results"]["known_location"]["total"]} known locations')
    return 0


if __name__ == '__main__':
    sys.exit(main())
