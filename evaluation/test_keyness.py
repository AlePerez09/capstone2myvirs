"""
MyVIRS Team A: the keyness relevance test in evaluation/KEYNESS_PROTOCOL.md.

1. Score the 8 pre-set keyness settings (2 formulas x 4 weights) on CK-12
   Biology only, and keep the best one by MAP (ties: smaller weight).
2. Run that one setting on the held-out CK-12 Trigonometry lessons (primary)
   and the learner-focused key (secondary), against count only with the same
   filters. Wilcoxon signed-rank, two-sided, on average precision.
3. Sensitivity: the same with number words kept.

Uses priority_ranking.rank_records(relevance="keyness") directly.

Usage:
    python3 evaluation/test_keyness.py --learner-key baseline-comparison/learner-key/answer_key.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402

FORMULAS = ["tf_rarity", "log_ratio"]
WEIGHTS = [0.25, 0.5, 0.75, 1.0]
FILTERS = dict(score_by="count", drop_generic_verbs=True, drop_numbers=True)


def count_only(filters):
    return dict(filters, frequency_weight=1.0, relevance_weight=0.0)


def keyness(formula, w, filters):
    return dict(filters, frequency_weight=1 - w, relevance_weight=w,
                relevance="keyness", keyness_formula=formula)


def aps(items, lexicon, opts):
    out = []
    for records, words in items:
        gold = ev.gold_set(words, ev.word_to_head(records))
        if gold:
            ranked = pr.rank_records(records, lexicon, **opts)
            out.append(ev.average_precision([r["headword"] for r in ranked], gold))
    return out


def test(a, b):
    try:
        p = float(wilcoxon(a, b).pvalue)
    except ValueError:
        p = None
    return {"map": round(float(np.mean(a)), 4), "compared_map": round(float(np.mean(b)), 4),
            "better": sum(x > y for x, y in zip(a, b)), "worse": sum(x < y for x, y in zip(a, b)),
            "tied": sum(x == y for x, y in zip(a, b)),
            "wilcoxon_p": None if p is None else round(p, 4),
            "significantly_better": bool(np.mean(a) > np.mean(b) and p is not None and p < 0.05)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--learner-key")
    ap.add_argument("--out", default=str(HERE / "results" / "keyness_test.json"))
    args = ap.parse_args()
    lexicon = pr.load_default_lexicon(verbose=False)

    bio = [(pipeline.analyze_text(l["text"]), l["first_words"])
           for l in ev.biology_lessons(ev.REPO / "data" / "biology.txt")]

    # Step 1: choose on Biology only
    tuning = []
    for formula in FORMULAS:
        for w in WEIGHTS:
            tuning.append({"formula": formula, "weight": w,
                           "biology_map": round(float(np.mean(aps(bio, lexicon, keyness(formula, w, FILTERS)))), 4)})
    best = sorted(tuning, key=lambda t: (-t["biology_map"], t["weight"]))[0]
    print("chosen on Biology:", best, flush=True)

    # Step 2: held-out tests, run once
    held = {"trigonometry": [(pipeline.analyze_text(l["text"]), l["first_words"])
                             for l in ev.trig_lessons(HERE / "data" / "trigonometry_spaced.txt",
                                                      HERE / "data" / "trigonometry_vocab_key.json")]}
    if args.learner_key:
        key = json.loads(Path(args.learner_key).read_text(encoding="utf-8"))
        held["learner_key"] = [(pipeline.analyze_text(p["text"]), p["key_words"]) for p in key]
    books = {"biology (tuned on)": bio, **held}

    report = {"protocol": "evaluation/KEYNESS_PROTOCOL.md", "tuning_on_biology": tuning,
              "chosen": best, "results": {}}
    for numbers_label, filters in [("numbers dropped (primary)", FILTERS),
                                   ("numbers kept (sensitivity)", dict(FILTERS, drop_numbers=False))]:
        chosen = keyness(best["formula"], best["weight"], filters)
        block = {}
        for name, items in books.items():
            k = aps(items, lexicon, chosen)
            c = aps(items, lexicon, count_only(filters))
            f = aps(items, lexicon, dict(frequency_only=True))
            t = aps(items, lexicon, dict(filters, frequency_weight=0.75, relevance_weight=0.25))
            block[name] = {"keyness_vs_count_only": test(k, c),
                           "keyness_vs_frequency_only": test(k, f),
                           "textrank_blend_vs_count_only": test(t, c)}
        report["results"][numbers_label] = block

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    for label, block in report["results"].items():
        print(f"\n{label}")
        for name, r in block.items():
            kc, tc = r["keyness_vs_count_only"], r["textrank_blend_vs_count_only"]
            print(f"  {name:<20} keyness {kc['map']:.3f} vs count {kc['compared_map']:.3f} "
                  f"({kc['better']}/{kc['worse']}, p={kc['wilcoxon_p']}) | "
                  f"textrank blend {tc['map']:.3f} (p={tc['wilcoxon_p']}) | "
                  f"freq-only {r['keyness_vs_frequency_only']['compared_map']:.3f}")


if __name__ == "__main__":
    main()
