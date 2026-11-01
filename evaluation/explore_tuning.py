"""
MyVIRS Team A, Sprint 4: EXPLORATORY tuning after the official evaluation.

The official result (run_evaluation.py) is "criterion not met" and stays
that way: evaluation_criterion.md fixed the 0.5 / 0.5 weights and band
scores in advance. The criterion also says how other settings may be tried:
"tune on Biology only and report the math book as the held-out test."
That is what this script does.

1. Run the pipeline once per lesson (plain, and with Fernando's options)
   and cache the records, so each setting is cheap to score.
2. Score every combination of the settings below on Biology only.
3. Pick the setting with the best Biology MAP.
4. Run that one setting on Trigonometry, which tuning never saw, and test it
   against the official frequency-only baseline with the same Wilcoxon test.

Settings tried (none of them looks at the answer key):
  frequency score  band (official), band with K1 > K2 > K3, band + grade
                   bonus, or the word's count percentile within the lesson
  relevance weight 0, 0.25, 0.5, 0.75, 1
  number words     kept (official) or dropped from the ranking
  generic verbs    kept or dropped (pipeline.TEXTBOOK_VERBS plus a few more)
  pipeline options plain, or weighted links + verb filter + abbreviations

Usage:
    python3 evaluation/explore_tuning.py --out evaluation/results/exploratory
"""

import argparse
import itertools
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402  (sets up the repo path, loads spaCy)
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402
from spacy.lang.en.stop_words import STOP_WORDS  # noqa: E402

EXTRA_GENERIC_VERBS = {"produce", "occur", "represent", "need", "help", "cause",
                       "form", "define", "determine", "contain", "allow", "become"}
GENERIC_VERBS = set(pipeline.TEXTBOOK_VERBS) | EXTRA_GENERIC_VERBS
K_SCORES = {"K1": 1.0, "K2": 0.8, "K3": 0.6}
WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]
FREQ_SCORES = ["band", "band_k", "band_grade", "count_pct"]
GRADE_FOR_BOOK = {"biology": "G10", "trigonometry": "G11"}  # CK-12 high-school books


def cache_records(name, lessons, path):
    if path.exists():
        return pickle.loads(path.read_bytes())
    out = []
    for lesson in lessons:
        plain = pipeline.analyze_text(lesson["text"])
        improved = pipeline.analyze_text(lesson["text"], weighted=True, filter_verbs=True,
                                         group_abbreviations=True)
        out.append({"id": lesson["id"], "title": lesson["title"],
                    "first_words": lesson["first_words"], "plain": plain, "improved": improved})
        print(f"cached {name} {lesson['id']}", flush=True)
    path.write_bytes(pickle.dumps(out))
    return out


def freq_score(kind, rec, entry, count_pct, grade):
    if kind == "count_pct":
        return count_pct
    if kind == "band_k" and entry.get("k_level") in K_SCORES:
        return K_SCORES[entry["k_level"]]
    if kind == "band_grade":
        return pr.band_score(entry, grade)
    return pr.band_score(entry)


def rank(records, lexicon, kind, w_rel, drop_numbers, drop_verbs, grade):
    kept = []
    for r in records:
        h = r["headword"]
        if h in pipeline.NUMBER_WORDS:
            if drop_numbers:
                continue
        elif r.get("is_stop") or h in STOP_WORDS or h in pr.LAYOUT_WORDS:
            continue
        if drop_verbs and h in GENERIC_VERBS:
            continue
        kept.append(r)
    if not kept:
        return []
    counts = [r["count"] for r in kept]
    pct = (rankdata(counts) - 1) / max(len(kept) - 1, 1)
    scored = []
    for r, cp in zip(kept, pct):
        f = freq_score(kind, r, pr.lookup(r, lexicon), cp, grade)
        p = (1 - w_rel) * f + w_rel * (r.get("relevance") or 0.0)
        scored.append((-p, -r["count"], r["headword"]))
    return [h for _, _, h in sorted(scored)]


def official_baseline(records, lexicon):
    return [r["headword"] for r in pr.rank_records(records, lexicon, frequency_only=True)]


def gold_for(lesson):
    return ev.gold_set(lesson["first_words"], ev.word_to_head(lesson["plain"]))


def score_setting(cached, lexicon, setting, book):
    kind, w_rel, drop_numbers, drop_verbs, variant = setting
    aps, p10s = [], []
    for lesson in cached:
        gold = gold_for(lesson)
        if not gold:
            continue
        if variant == "improved":
            gold = gold | ev.gold_set(lesson["first_words"], ev.word_to_head(lesson["plain"]), abbrev=True)
        ranked = rank(lesson[variant], lexicon, kind, w_rel, drop_numbers, drop_verbs,
                      GRADE_FOR_BOOK[book])
        aps.append(ev.average_precision(ranked, gold))
        p10s.append(ev.precision_at(ranked, gold, 10))
    return aps, p10s


def baseline_scores(cached, lexicon):
    aps, p10s = [], []
    for lesson in cached:
        gold = gold_for(lesson)
        if not gold:
            continue
        ranked = official_baseline(lesson["plain"], lexicon)
        aps.append(ev.average_precision(ranked, gold))
        p10s.append(ev.precision_at(ranked, gold, 10))
    return aps, p10s


def test(a, b):
    try:
        p = float(wilcoxon(a, b).pvalue)
    except ValueError:
        p = None
    return {"map": float(np.mean(a)), "baseline_map": float(np.mean(b)),
            "better": sum(x > y for x, y in zip(a, b)), "worse": sum(x < y for x, y in zip(a, b)),
            "tied": sum(x == y for x, y in zip(a, b)), "wilcoxon_p": p,
            "significant_win": bool(np.mean(a) > np.mean(b) and p is not None and p < 0.05)}


def label(s):
    kind, w, dn, dv, var = s
    return (f"{kind}, relevance weight {w}, numbers {'dropped' if dn else 'kept'}, "
            f"generic verbs {'dropped' if dv else 'kept'}, pipeline {var}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results" / "exploratory"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lexicon = pr.load_default_lexicon()

    bio = cache_records("biology", ev.biology_lessons(ev.REPO / "data" / "biology.txt"),
                        out / "cache_biology.pkl")
    trig = cache_records("trigonometry",
                         ev.trig_lessons(HERE / "data" / "trigonometry_spaced.txt",
                                         HERE / "data" / "trigonometry_vocab_key.json"),
                         out / "cache_trigonometry.pkl")

    bio_base, _ = baseline_scores(bio, lexicon)
    trig_base, _ = baseline_scores(trig, lexicon)

    settings = list(itertools.product(FREQ_SCORES, WEIGHTS, [False, True], [False, True],
                                      ["plain", "improved"]))
    grid = []
    for s in settings:
        aps, p10s = score_setting(bio, lexicon, s, "biology")
        grid.append({"setting": label(s), "params": s, "biology_map": float(np.mean(aps)),
                     "biology_p@10": float(np.mean(p10s))})
    grid.sort(key=lambda g: -g["biology_map"])

    # Best COMBINED setting (both a frequency part and a relevance part)
    combined_only = [g for g in grid if 0 < g["params"][1] < 1]
    chosen = [("best combined setting on Biology", combined_only[0]),
              ("best setting of any kind on Biology", grid[0])]
    report = {"baseline": "priority_ranking.py --frequency-only (official)",
              "biology_baseline_map": float(np.mean(bio_base)),
              "trigonometry_baseline_map": float(np.mean(trig_base)),
              "settings_tried": len(grid), "chosen": []}
    for why, g in chosen:
        b_aps, b_p10 = score_setting(bio, lexicon, g["params"], "biology")
        t_aps, t_p10 = score_setting(trig, lexicon, g["params"], "trigonometry")
        bt, tt = test(b_aps, bio_base), test(t_aps, trig_base)
        report["chosen"].append({
            "why": why, "setting": g["setting"],
            "biology_tuned_in_sample": {**bt, "p@10": float(np.mean(b_p10))},
            "trigonometry_held_out": {**tt, "p@10": float(np.mean(t_p10))},
            "would_meet_criterion": bt["significant_win"] and tt["significant_win"],
        })
    report["top20_on_biology"] = [{k: v for k, v in g.items() if k != "params"} for g in grid[:20]]
    # Trig scores for every setting, for transparency only (NOT used to choose)
    tgrid = []
    for g in grid:
        t_aps, _ = score_setting(trig, lexicon, g["params"], "trigonometry")
        tgrid.append({"setting": g["setting"], "biology_map": round(g["biology_map"], 4),
                      "trigonometry_map": round(float(np.mean(t_aps)), 4)})
    report["all_settings_both_books_for_reference_only"] = tgrid
    (out / "tuning_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("all_settings_both_books_for_reference_only",)}, indent=1))


if __name__ == "__main__":
    main()
