#!/usr/bin/env python3
"""Compare two local transcript texts lexically, not semantically or by recording.

Five-token shingles and exact normalized word runs are reproducible review
clues. They do not establish duplication, recording identity, or accuracy.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ayman_rag.search import CATALOG, ROOT, WORD, normalize, read_verified  # noqa: E402

K = 5
STAMP = re.compile(r'\*\*\[\d{1,2}:\d{2}(?::\d{2})?\]\([^)]*\)\*\*')
URL = re.compile(r'https?://\S+')


def tokens_by_line(text):
    words, lines = [], []
    for n, line in enumerate(text.splitlines(), 1):
        # Suppress timestamp link markup and URLs only for comparison; the
        # line numbers still address the unchanged original file.
        clean = URL.sub(' ', STAMP.sub(' ', line))
        for token in WORD.findall(normalize(clean)):
            words.append(token)
            lines.append(n)
    return words, lines


def shingles(words, k=K):
    return [tuple(words[i:i + k]) for i in range(max(0, len(words) - k + 1))]


def positional_bins(seq, other, bins=10):
    other_set = set(other)
    length = len(seq)
    result = []
    for i in range(bins):
        start, end = i * length // bins, (i + 1) * length // bins
        count = end - start
        matched = sum(s in other_set for s in seq[start:end])
        result.append({'start_shingle': start + 1 if count else None, 'end_shingle': end if count else None,
                       'matched': matched, 'total': count})
    return result


def compare_texts(a, b, max_runs=10):
    if not 0 <= max_runs <= 50:
        raise ValueError('max_runs must be between 0 and 50')
    wa, la = tokens_by_line(a); wb, lb = tokens_by_line(b)
    sa, sb = shingles(wa), shingles(wb)
    ca, cb = Counter(sa), Counter(sb)
    common = ca.keys() & cb.keys()
    union = ca.keys() | cb.keys()
    positions_b = {s: i for i, s in enumerate(sb) if cb[s] == 1}
    anchors = [(i, positions_b[s]) for i, s in enumerate(sa) if ca[s] == 1 and s in positions_b]
    runs = []
    if anchors:
        first_a, first_b = anchors[0]
        last_a, last_b = first_a, first_b
        for ia, ib in anchors[1:] + [(None, None)]:
            if ia == last_a + 1 and ib == last_b + 1:
                last_a, last_b = ia, ib
                continue
            length = last_a - first_a + K
            if length >= 10:
                runs.append({'words': length,
                             'a_start_line': la[first_a], 'a_end_line': la[last_a + K - 1],
                             'b_start_line': lb[first_b], 'b_end_line': lb[last_b + K - 1],
                             'normalized_preview': ' '.join(wa[first_a:first_a + min(length, 12)])})
            first_a, first_b = ia, ib
            last_a, last_b = ia, ib
    runs.sort(key=lambda r: (-r['words'], r['a_start_line'], r['b_start_line']))
    return {'k': K, 'a_tokens': len(wa), 'b_tokens': len(wb),
            'a_unique_shingles': len(ca), 'b_unique_shingles': len(cb), 'shared_unique_shingles': len(common),
            'unique_jaccard': len(common) / len(union) if union else None,
            'shared_over_smaller': len(common) / min(len(ca), len(cb)) if ca and cb else None,
            'a_position_bins': positional_bins(sa, sb), 'b_position_bins': positional_bins(sb, sa),
            'unique_anchor_runs': runs[:max_runs], 'unique_anchor_run_count': len(runs)}


def compare_sources(source_a, source_b, catalog_path=CATALOG, root=ROOT, max_runs=10):
    docs = json.loads(catalog_path.read_text(encoding='utf-8'))['documents']
    catalog = {d['id']: d for d in docs}
    if len(catalog) != len(docs):
        raise ValueError('duplicate source IDs')
    if source_a == source_b:
        raise ValueError('choose two distinct source IDs')
    if source_a not in catalog or source_b not in catalog:
        raise ValueError('unknown source ID')
    a, b = catalog[source_a], catalog[source_b]
    result = compare_texts(read_verified(a, root), read_verified(b, root), max_runs=max_runs)
    for label, doc in [('a', a), ('b', b)]:
        result[label] = {k: doc[k] for k in ('id', 'path', 'sha256')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_a'); parser.add_argument('source_b')
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--max-runs', type=int, default=10)
    args = parser.parse_args()
    try:
        print(json.dumps(compare_sources(args.source_a, args.source_b, args.catalog, max_runs=args.max_runs), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'error: {exc}\n')


if __name__ == '__main__':
    main()
