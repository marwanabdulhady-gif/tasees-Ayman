"""Stage 2 — measure the retriever, so every change can be compared with a number.

For each test question we know which lecture(s) hold the answer. We search,
then look at the lecture each returned chunk came from.

Two scores:
- Hit@k: share of questions where a right lecture appears anywhere in the top k.
  "Did the LLM get to see the answer at all?"
- MRR (mean reciprocal rank): 1 if the right lecture is first, 1/2 if second,
  1/3 if third... averaged. "How high up was it?"
"""

import json
from pathlib import Path


def load_questions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def first_hit_rank(results, relevant: set[str]) -> int | None:
    for rank, (chunk, _) in enumerate(results, 1):
        if f"{chunk.course}/{chunk.lecture_number}" in relevant:
            return rank
    return None


def evaluate(retriever, questions: list[dict], top_k: int = 5) -> dict:
    rows = []
    for q in questions:
        results = retriever.search(q["question"], top_k)
        rank = first_hit_rank(results, set(q["relevant"]))
        rows.append({**q, "rank": rank, "top": results[0][0].citation() if results else "—"})

    def summary(subset):
        n = len(subset) or 1
        return {
            "n": len(subset),
            "hit": sum(r["rank"] is not None for r in subset) / n,
            "mrr": sum(1 / r["rank"] for r in subset if r["rank"]) / n,
        }

    return {
        "rows": rows,
        "all": summary(rows),
        "by_type": {t: summary([r for r in rows if r["type"] == t]) for t in sorted({r["type"] for r in rows})},
    }


def print_report(report: dict, top_k: int) -> None:
    for r in report["rows"]:
        mark = f"#{r['rank']}" if r["rank"] else "miss"
        print(f"{r['id']}  {mark:>4}  {r['type']:<10}  {r['question']}")
        if not r["rank"]:
            print(f"                 top result instead: {r['top']}")
    print()
    for name, s in [("all", report["all"]), *report["by_type"].items()]:
        print(f"{name:<11} Hit@{top_k} {s['hit']:.0%}  ({round(s['hit'] * s['n'])}/{s['n']})   MRR {s['mrr']:.2f}")
