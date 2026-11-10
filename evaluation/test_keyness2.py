"""
MyVIRS Team A: the second relevance test in evaluation/KEYNESS2_PROTOCOL.md.

1. Score 12 pre-set settings (3 relevance scores x 4 weights) on Biology
   and Trigonometry; keep the best by the average of the two books' MAPs.
2. Run that one setting once on the fresh books (Chemistry, Basic Geometry
   Concepts, Basic Algebra Concepts) against count only, same filters.

Needs evaluation/data/fresh/ from fresh_books.py.

    python3 evaluation/test_keyness2.py
"""

import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402

FRESH = HERE / "data" / "fresh"
FILTERS = dict(score_by="count", drop_generic_verbs=True, drop_numbers=True)
SCORES = ["english", "textbooks", "both"]
WEIGHTS = [0.25, 0.5, 0.75, 1.0]
CHUNK = 1500


def chunks(text):
    words = re.findall(r"[a-z]+", text.lower())
    return [set(words[k:k + CHUNK]) for k in range(0, len(words), CHUNK)]


class Pile:
    """Reference textbook pile: which chunks each word appears in."""

    def __init__(self, books):
        self.index, self.book_of = {}, []
        for book, chunk_list in books.items():
            for c in chunk_list:
                cid = len(self.book_of)
                self.book_of.append(book)
                for w in c:
                    self.index.setdefault(w, set()).add(cid)

    def scorer(self, leave_out=None):
        keep = {i for i, b in enumerate(self.book_of) if b != leave_out}
        n = len(keep)

        def df(forms):
            hit = set()
            for f in forms:
                hit |= self.index.get(f, set())
            return len(hit & keep)
        return df, n


def textbook_keyness(records, df_fn, n):
    raw = [r["count"] * math.log((n + 1) / (df_fn({r["headword"], *r.get("forms", [])}) + 1))
           for r in records]
    return pr.count_percentiles(raw)


def relevance_for(kept, kind, pile_scorer):
    if kind == "english":
        return pr.keyness_scores(kept, "log_ratio")
    tb = textbook_keyness(kept, *pile_scorer)
    if kind == "textbooks":
        return tb
    en = pr.keyness_scores(kept, "log_ratio")
    return [(a + b) / 2 for a, b in zip(en, tb)]


def rank(records, lexicon, kind, w, pile_scorer):
    kept = pr.rank_records(records, lexicon, **FILTERS, frequency_weight=1.0, relevance_weight=0.0)
    if kind is None:
        return [r["headword"] for r in kept]
    rel = relevance_for(kept, kind, pile_scorer)
    rows = [dict(r, relevance=x) for r, x in zip(kept, rel)]
    ranked = pr.rank_records(rows, lexicon, **FILTERS, frequency_weight=1 - w, relevance_weight=w)
    return [r["headword"] for r in ranked]


def book_aps(items, lexicon, kind, w, pile_scorer, frequency_only=False):
    out = []
    for records, words in items:
        gold = ev.gold_set(words, ev.word_to_head(records))
        if not gold:
            continue
        if frequency_only:
            heads = [r["headword"] for r in pr.rank_records(records, lexicon, frequency_only=True)]
        else:
            heads = rank(records, lexicon, kind, w, pile_scorer)
        out.append(ev.average_precision(heads, gold))
    return out


def test(a, b):
    try:
        p = float(wilcoxon(a, b).pvalue)
    except ValueError:
        p = None
    return {"n": len(a), "map": round(float(np.mean(a)), 4), "count_only_map": round(float(np.mean(b)), 4),
            "better": sum(x > y for x, y in zip(a, b)), "worse": sum(x < y for x, y in zip(a, b)),
            "wilcoxon_p": None if p is None else float(f"{p:.3g}")}


def main():
    lexicon = pr.load_default_lexicon(verbose=False)
    bio_lessons = ev.biology_lessons(ev.REPO / "data" / "biology.txt")
    trig_path = HERE / "data" / "trigonometry_spaced.txt"
    trig_lessons = ev.trig_lessons(trig_path, HERE / "data" / "trigonometry_vocab_key.json")

    books = {k: [set(c) for c in v]
             for k, v in json.loads((FRESH / "reference_pile.json").read_text()).items()}
    books["biology"] = chunks((ev.REPO / "data" / "biology.txt").read_text(encoding="utf-8"))
    books["trigonometry"] = chunks(trig_path.read_text(encoding="utf-8"))
    pile = Pile(books)

    seen = {"biology": ([(pipeline.analyze_text(l["text"]), l["first_words"]) for l in bio_lessons],
                        pile.scorer("biology")),
            "trigonometry": ([(pipeline.analyze_text(l["text"]), l["first_words"]) for l in trig_lessons],
                             pile.scorer("trigonometry"))}

    tuning = []
    for kind in SCORES:
        for w in WEIGHTS:
            row = {"relevance": kind, "weight": w}
            for name, (items, sc) in seen.items():
                row[name] = round(float(np.mean(book_aps(items, lexicon, kind, w, sc))), 4)
            row["average"] = round((row["biology"] + row["trigonometry"]) / 2, 4)
            tuning.append(row)
            print(row, flush=True)
    best = sorted(tuning, key=lambda t: (-t["average"], t["weight"]))[0]
    print("CHOSEN:", best, flush=True)

    sc = pile.scorer()
    fresh = {}
    for name in ["chemistry", "geometry", "algebra"]:
        lessons = json.loads((FRESH / f"{name}_lessons.json").read_text(encoding="utf-8"))
        fresh[name] = [(pipeline.analyze_text(l["text"]), l["first_words"]) for l in lessons]

    report = {"protocol": "evaluation/KEYNESS2_PROTOCOL.md", "tuning": tuning, "chosen": best,
              "seen_books_count_only": {n: round(float(np.mean(book_aps(it, lexicon, None, 0, s))), 4)
                                        for n, (it, s) in seen.items()},
              "fresh": {}}
    pooled = {"all": ([], []), "math": ([], [])}
    for name, items in fresh.items():
        k = book_aps(items, lexicon, best["relevance"], best["weight"], sc)
        c = book_aps(items, lexicon, None, 0, sc)
        f = book_aps(items, lexicon, None, 0, sc, frequency_only=True)
        report["fresh"][name] = {**test(k, c), "frequency_only_map": round(float(np.mean(f)), 4)}
        pooled["all"][0].extend(k); pooled["all"][1].extend(c)
        if name != "chemistry":
            pooled["math"][0].extend(k); pooled["math"][1].extend(c)
    report["fresh"]["pooled_all"] = test(*pooled["all"])
    report["fresh"]["pooled_math"] = test(*pooled["math"])
    pa, pm = report["fresh"]["pooled_all"], report["fresh"]["pooled_math"]
    report["passes"] = bool(pa["map"] > pa["count_only_map"] and pa["wilcoxon_p"] is not None
                            and pa["wilcoxon_p"] < 0.05 and pm["map"] >= pm["count_only_map"])
    (HERE / "results" / "keyness2_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("chosen", "seen_books_count_only", "fresh", "passes")}, indent=1))


if __name__ == "__main__":
    main()
