#!/usr/bin/env python3
"""Report known-location lexical retrieval, not answer quality or exhaustive relevance."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ayman_rag.search import CATALOG, INDEX, ROOT, read_verified, search  # noqa: E402

CASES = Path(__file__).with_name('eval_cases.json')


def target_rank(results, case):
    for rank, result in enumerate(results, 1):
        if (result['source_id'] == case['source_id'] and
                result['start_line'] <= case['line'] <= result['end_line']):
            return rank
    return None


def evaluate(cases_path=CASES, match='any', catalog_path=CATALOG, index_path=INDEX):
    dataset = json.loads(cases_path.read_text(encoding='utf-8'))
    catalog = {d['id']: d for d in json.loads(catalog_path.read_text(encoding='utf-8'))['documents']}
    ranks = []
    for case in dataset['cases']:
        if case['source_id'] not in catalog:
            raise ValueError(f"unknown reference source {case['source_id']}")
        lines = read_verified(catalog[case['source_id']], ROOT).splitlines()
        line = case['line']
        if not isinstance(line, int) or line < 1 or line > len(lines) or not case['quote'] or case['quote'] not in lines[line - 1]:
            raise ValueError(f"reference quote/line invalid for {case['source_id']}")
        rank = target_rank(search(case['query'], index_path=index_path, catalog_path=catalog_path, limit=dataset['limit'], match=match), case)
        ranks.append(rank)
        print(f"{case['query']} | {case['source_id']} L{line} | " + (f'rank {rank}' if rank else 'not in top results'))
    print(f"Known-location hits@{dataset['limit']} ({match}): {sum(r is not None for r in ranks)}/{len(ranks)}")
    print('Other results are unjudged; this does not measure semantic relevance or answer correctness.')
    return ranks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--match', choices=('any', 'all'), default='any')
    parser.add_argument('--cases', type=Path, default=CASES)
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--index', type=Path, default=INDEX)
    args = parser.parse_args()
    try:
        evaluate(cases_path=args.cases, match=args.match, catalog_path=args.catalog, index_path=args.index)
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f'error: {exc}')
