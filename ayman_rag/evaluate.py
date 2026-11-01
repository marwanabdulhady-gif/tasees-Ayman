#!/usr/bin/env python3
"""Report known-location lexical retrieval, not answer quality or exhaustive relevance."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ayman_rag.search import CATALOG, ROOT, read_verified, search  # noqa: E402

CASES = Path(__file__).with_name('eval_cases.json')


def target_rank(results, case):
    for rank, result in enumerate(results, 1):
        if (result['source_id'] == case['source_id'] and
                result['start_line'] <= case['line'] <= result['end_line']):
            return rank
    return None


def evaluate(cases_path=CASES):
    dataset = json.loads(cases_path.read_text(encoding='utf-8'))
    catalog = {d['id']: d for d in json.loads(CATALOG.read_text(encoding='utf-8'))['documents']}
    ranks = []
    for case in dataset['cases']:
        if case['source_id'] not in catalog:
            raise ValueError(f"unknown reference source {case['source_id']}")
        lines = read_verified(catalog[case['source_id']], ROOT).splitlines()
        line = case['line']
        if not isinstance(line, int) or line < 1 or line > len(lines) or not case['quote'] or case['quote'] not in lines[line - 1]:
            raise ValueError(f"reference quote/line invalid for {case['source_id']}")
        rank = target_rank(search(case['query'], limit=dataset['limit']), case)
        ranks.append(rank)
        print(f"{case['query']} | {case['source_id']} L{line} | " + (f'rank {rank}' if rank else 'not in top results'))
    print(f"Known-location hits@{dataset['limit']}: {sum(r is not None for r in ranks)}/{len(ranks)}")
    print('Other results are unjudged; this does not measure semantic relevance or answer correctness.')
    return ranks


if __name__ == '__main__':
    try:
        evaluate()
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f'error: {exc}')
