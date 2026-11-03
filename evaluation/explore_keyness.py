"""
MyVIRS Team A, Sprint 5: EXPLORATORY look at a different relevance signal.

Not part of any official result and not pre-registered. Two ideas were tried
once each, with three blend weights, and nothing was tuned on the answer key.

Today "relevance" is TextRank: words linked to many other words score high.
In the Sprint 4 evaluation that rewards generic hub words (water, form,
produce) and adds nothing beyond counting. This script swaps TextRank for a
"keyness" score: how much more a word is used in this lesson than you'd
expect from how common it is elsewhere.

  keyness_english  count in lesson x (8 - Zipf frequency in general English,
                   from the wordfreq package). Needs no corpus of our own,
                   so it works on a single learner passage.
  keyness_book     count in lesson x log(lessons / lessons using the word),
                   i.e. TF-IDF against the other lessons of the same book.
                   Needs a set of related texts, which MyVIRS usually won't
                   have (see approach_decision_textrank_vs_tfidf.md).

Each keyness score is turned into a percentile within the lesson and used
as the relevance part of priority_ranking.rank_records(), with the Sprint 5
options (count percentile, generic verbs and number words dropped).

Usage:
    python3 evaluation/explore_keyness.py --learner-key baseline-comparison/learner-key/answer_key.json
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon
from wordfreq import zipf_frequency

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402

BASE = dict(pr.RECOMMENDED, drop_numbers=True)
SETTINGS = [
    # name, relevance source, rank_records options
    ("frequency_only (official baseline)", "textrank", dict(frequency_only=True)),
    ("count only", "textrank", dict(BASE, frequency_weight=1.0, relevance_weight=0.0)),
    ("0.75 count + 0.25 TextRank", "textrank", BASE),
    ("TextRank only", "textrank", dict(BASE, frequency_weight=0.0, relevance_weight=1.0)),
]
for source in ("keyness_english", "keyness_book"):
    SETTINGS += [
        (f"{source} only", source, dict(BASE, frequency_weight=0.0, relevance_weight=1.0)),
        (f"0.75 count + 0.25 {source}", source, BASE),
        (f"0.5 count + 0.5 {source}", source, dict(BASE, frequency_weight=0.5, relevance_weight=0.5)),
    ]
COMPARE_TO = "count only"


def doc_freq(record_sets):
    d = {}
    for records in record_sets:
        for h in {r["headword"] for r in records}:
            d[h] = d.get(h, 0) + 1
    return d, len(record_sets)


def with_relevance(records, source, df):
    if source == "textrank":
        return records
    if source == "keyness_english":
        raw = [r["count"] * max(0.5, 8 - zipf_frequency(r["headword"], "en")) for r in records]
    else:
        d, n = df
        raw = [r["count"] * math.log((n + 1) / (d.get(r["headword"], 0) + 1)) for r in records]
    return [dict(r, relevance=p) for r, p in zip(records, pr.count_percentiles(raw))]


def evaluate(items, df, lexicon):
    aps = {name: [] for name, _, _ in SETTINGS}
    for records, words in items:
        gold = ev.gold_set(words, ev.word_to_head(records))
        if not gold:
            continue
        for name, source, opts in SETTINGS:
            ranked = pr.rank_records(with_relevance(records, source, df), lexicon, **opts)
            aps[name].append(ev.average_precision([r["headword"] for r in ranked], gold))
    out = {}
    for name, v in aps.items():
        try:
            p = None if name == COMPARE_TO else float(wilcoxon(v, aps[COMPARE_TO]).pvalue)
        except ValueError:
            p = None
        out[name] = {"map": round(float(np.mean(v)), 4),
                     "wilcoxon_p_vs_count_only": None if p is None else round(p, 4)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--learner-key")
    ap.add_argument("--out", default=str(HERE / "results" / "exploratory" / "keyness.json"))
    args = ap.parse_args()
    lexicon = pr.load_default_lexicon(verbose=False)

    bio = [(pipeline.analyze_text(l["text"]), l["first_words"])
           for l in ev.biology_lessons(ev.REPO / "data" / "biology.txt")]
    trig = [(pipeline.analyze_text(l["text"]), l["first_words"])
            for l in ev.trig_lessons(HERE / "data" / "trigonometry_spaced.txt",
                                     HERE / "data" / "trigonometry_vocab_key.json")]
    bio_df, trig_df = doc_freq([r for r, _ in bio]), doc_freq([r for r, _ in trig])
    report = {"biology": evaluate(bio, bio_df, lexicon),
              "trigonometry": evaluate(trig, trig_df, lexicon)}
    if args.learner_key:
        key = json.loads(Path(args.learner_key).read_text(encoding="utf-8"))
        learner = [(pipeline.analyze_text(p["text"]), p["key_words"]) for p in key]
        # learner passages are Biology excerpts: book keyness uses the Biology lessons
        report["learner_key"] = evaluate(learner, bio_df, lexicon)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    books = list(report)
    print(f"{'MAP':<40}" + "".join(f"{b:>16}" for b in books))
    for name, _, _ in SETTINGS:
        print(f"{name:<40}" + "".join(f"{report[b][name]['map']:>16.3f}" for b in books))


if __name__ == "__main__":
    main()
