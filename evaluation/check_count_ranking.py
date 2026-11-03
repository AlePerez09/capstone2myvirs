"""
MyVIRS Team A, Sprint 5: check the new priority_ranking.py options.

The Sprint 4 exploratory tuning (explore_tuning.py) found a setting that
beats frequency-only: 0.75 x the word's count percentile in the lesson
+ 0.25 x relevance, with number words and generic verbs dropped. Those
options are now built into priority_ranking.rank_records() (score_by,
drop_generic_verbs, drop_numbers; RECOMMENDED). This script runs the
real rank_records() code, not a copy of the tuning code, on the same
lessons and answer keys as run_evaluation.py, and tests each setting
against the official frequency-only baseline.

Answer keys:
  - CK-12 Biology (84 lessons) and Trigonometry (22 lessons) Vocabulary
    lists, first word of each term, exactly as in run_evaluation.py.
  - The learner-focused key (13 Biology passages, words a learner needs
    first to understand the passage's main topics), if --learner-key is
    given. One labeler, so treat it as a second opinion, not a verdict.

Usage:
    python3 evaluation/check_count_ranking.py --out evaluation/results/count_ranking \\
        [--learner-key baseline-comparison/learner-key/answer_key.json]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402  (sets up the repo path, loads spaCy)
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402

BASELINE = "frequency_only"
SETTINGS = {
    # name: rank_records() options
    "frequency_only": dict(frequency_only=True),               # official baseline
    "combined_official": dict(),                                # Sprint 4 tested setting
    "recommended": dict(pr.RECOMMENDED),                        # numbers kept (default)
    "recommended_drop_numbers": dict(pr.RECOMMENDED, drop_numbers=True),
    "count_no_relevance": dict(pr.RECOMMENDED, frequency_weight=1.0, relevance_weight=0.0),
    "count_no_relevance_drop_numbers": dict(pr.RECOMMENDED, frequency_weight=1.0,
                                            relevance_weight=0.0, drop_numbers=True),
}


def rank_all(records, lexicon):
    return {name: [r["headword"] for r in pr.rank_records(records, lexicon, **opts)]
            for name, opts in SETTINGS.items()}


def score(items, lexicon):
    """items: list of (id, text, key words). Returns per-item rows."""
    rows = []
    for item_id, text, words in items:
        records = pipeline.analyze_text(text)
        gold = ev.gold_set(words, ev.word_to_head(records))
        if not gold:
            continue
        ranked = rank_all(records, lexicon)
        row = {"id": item_id, "gold": sorted(gold)}
        for name, heads in ranked.items():
            row[f"{name}_ap"] = ev.average_precision(heads, gold)
            row[f"{name}_p@10"] = ev.precision_at(heads, gold, 10)
            row[f"{name}_top10"] = heads[:10]
        rows.append(row)
        print(f"  {item_id}", flush=True)
    return rows


def compare(rows, name):
    a = [r[f"{name}_ap"] for r in rows]
    b = [r[f"{BASELINE}_ap"] for r in rows]
    try:
        p = float(wilcoxon(a, b).pvalue)
    except ValueError:
        p = None
    return {"map": round(float(np.mean(a)), 4),
            "p@10": round(float(np.mean([r[f"{name}_p@10"] for r in rows])), 4),
            "better": sum(x > y for x, y in zip(a, b)),
            "worse": sum(x < y for x, y in zip(a, b)),
            "tied": sum(x == y for x, y in zip(a, b)),
            "wilcoxon_p_vs_baseline": None if p is None else round(p, 6),
            "beats_baseline": bool(np.mean(a) > np.mean(b) and p is not None and p < 0.05)}


def summarize(rows):
    return {"items": len(rows), **{name: compare(rows, name) for name in SETTINGS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results" / "count_ranking"))
    ap.add_argument("--learner-key", help="learner-focused answer_key.json (optional)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lexicon = pr.load_default_lexicon()

    books = {
        "biology": [(l["id"], l["text"], l["first_words"])
                    for l in ev.biology_lessons(ev.REPO / "data" / "biology.txt")],
        "trigonometry": [(l["id"], l["text"], l["first_words"])
                         for l in ev.trig_lessons(HERE / "data" / "trigonometry_spaced.txt",
                                                  HERE / "data" / "trigonometry_vocab_key.json")],
    }
    if args.learner_key:
        key = json.loads(Path(args.learner_key).read_text(encoding="utf-8"))
        books["learner_key"] = [(p["id"], p["text"], p["key_words"]) for p in key]

    summary, detail = {"settings": {k: str(v) for k, v in SETTINGS.items()}}, {}
    for name, items in books.items():
        print(name, flush=True)
        rows = score(items, lexicon)
        summary[name] = summarize(rows)
        detail[name] = rows
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "per_item.json").write_text(json.dumps(detail, indent=1), encoding="utf-8")

    print(f"\n{'setting':<34}" + "".join(f"{b:>22}" for b in books))
    for name in SETTINGS:
        cells = []
        for b in books:
            s = summary[b][name]
            p = s["wilcoxon_p_vs_baseline"]
            cells.append(f"{s['map']:.3f} ({s['better']}/{s['worse']}, p={p if p is not None else '-'})"
                         if name != BASELINE else f"{s['map']:.3f}")
        print(f"{name:<34}" + "".join(f"{c:>22}" for c in cells))


if __name__ == "__main__":
    main()
