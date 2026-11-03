"""
MyVIRS Team A: the third relevance test in evaluation/KEYNESS3_PROTOCOL.md
(subject-aware relevance).

1. Set the math-detector threshold on the five seen books (book subject only).
2. Choose the science setting on Biology + Chemistry and the math setting on
   Trigonometry + Geometry + Algebra (13 options each, "none" included).
3. Run once on the fresh books (Earth Science MS, Advanced Probability and
   Statistics Concepts) against count only.

    python3 evaluation/test_keyness3.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402
from test_keyness2 import Pile, chunks, book_aps, test, SCORES, WEIGHTS  # noqa: E402

FRESH = HERE / "data" / "fresh"
MATH_CHARS = set("0123456789=+−×÷^√πθ∑∫°<>≤≥±/")
OPTIONS = [(None, 0.0)] + [(k, w) for k in SCORES for w in WEIGHTS]


def math_score(text):
    chars = [c for c in text if not c.isspace()]
    return sum(c in MATH_CHARS for c in chars) / max(len(chars), 1)


def best_threshold(scored):
    """scored: (math_score, is_math). Threshold with the best accuracy."""
    cands = sorted({s for s, _ in scored})
    best = (0, 0)
    for i in range(len(cands) - 1):
        t = (cands[i] + cands[i + 1]) / 2
        acc = sum((s > t) == m for s, m in scored) / len(scored)
        if acc > best[0]:
            best = (acc, t)
    return best[1], best[0]


def load_json_book(name):
    return json.loads((FRESH / f"{name}_lessons.json").read_text(encoding="utf-8"))


def main():
    lexicon = pr.load_default_lexicon(verbose=False)
    trig_path = HERE / "data" / "trigonometry_spaced.txt"
    texts = {
        "biology": ev.biology_lessons(ev.REPO / "data" / "biology.txt"),
        "trigonometry": ev.trig_lessons(trig_path, HERE / "data" / "trigonometry_vocab_key.json"),
        "chemistry": load_json_book("chemistry"),
        "geometry": load_json_book("geometry"),
        "algebra": load_json_book("algebra"),
    }
    subject = {"biology": "science", "chemistry": "science",
               "trigonometry": "math", "geometry": "math", "algebra": "math"}
    pile_books = {k: [set(c) for c in v]
                  for k, v in json.loads((FRESH / "reference_pile_3.json").read_text()).items()}
    pile_books["biology"] = chunks((ev.REPO / "data" / "biology.txt").read_text(encoding="utf-8"))
    pile_books["trigonometry"] = chunks(trig_path.read_text(encoding="utf-8"))
    pile = Pile(pile_books)
    pdf_name = {"chemistry": "ck12_chemistry", "geometry": "ck12_basic_geometry_concepts",
                "algebra": "ck12_basic_algebra_concepts"}

    # 1. detector threshold
    scored = [(math_score(l["text"]), subject[b] == "math") for b, ls in texts.items() for l in ls]
    threshold, acc = best_threshold(scored)
    print(f"math threshold {threshold:.4f}, accuracy on seen lessons {acc:.3f}", flush=True)

    # 2. choose settings
    seen = {b: ([(pipeline.analyze_text(l["text"]), l["first_words"]) for l in ls],
                pile.scorer(pdf_name.get(b, b))) for b, ls in texts.items()}
    choice, grid = {}, {}
    for subj in ("science", "math"):
        books = [b for b in seen if subject[b] == subj]
        rows = []
        for kind, w in OPTIONS:
            maps = {b: round(float(np.mean(book_aps(seen[b][0], lexicon, kind, w, seen[b][1]))), 4)
                    for b in books}
            rows.append({"relevance": kind or "none", "weight": w, **maps,
                         "average": round(float(np.mean(list(maps.values()))), 4)})
        rows.sort(key=lambda r: (-r["average"], r["weight"]))
        grid[subj] = rows
        choice[subj] = rows[0]
        print(subj, "chosen:", rows[0], flush=True)

    # 3. fresh test, run once
    sc = pile.scorer()
    fresh_subject = {"earth_science": "science", "prob_stats": "math"}
    report = {"protocol": "evaluation/KEYNESS3_PROTOCOL.md", "threshold": threshold,
              "detector_accuracy_seen": acc, "choice": choice, "grid": grid, "fresh": {}}
    pooled = {"detector": ([], []), "true_subject": ([], [])}
    for name, subj in fresh_subject.items():
        lessons = load_json_book(name)
        k_det, k_true, c, f, labels = [], [], [], [], []
        for l in lessons:
            records = pipeline.analyze_text(l["text"])
            item = [(records, l["first_words"])]
            if not ev.gold_set(l["first_words"], ev.word_to_head(records)):
                continue
            det = "math" if math_score(l["text"]) > threshold else "science"
            labels.append(det)
            for lst, s in ((k_det, det), (k_true, subj)):
                ch = choice[s]
                kind = None if ch["relevance"] == "none" else ch["relevance"]
                lst.extend(book_aps(item, lexicon, kind, ch["weight"], sc))
            c.extend(book_aps(item, lexicon, None, 0, sc))
            f.extend(book_aps(item, lexicon, None, 0, sc, frequency_only=True))
        report["fresh"][name] = {"detector": test(k_det, c), "true_subject": test(k_true, c),
                                 "frequency_only_map": round(float(np.mean(f)), 4),
                                 "lessons_labeled_math": labels.count("math"), "lessons": len(labels)}
        for key, lst in (("detector", k_det), ("true_subject", k_true)):
            pooled[key][0].extend(lst); pooled[key][1].extend(c)
    report["fresh"]["pooled"] = {k: test(*v) for k, v in pooled.items()}
    p, m = report["fresh"]["pooled"]["detector"], report["fresh"]["prob_stats"]["detector"]
    report["passes"] = bool(p["map"] > p["count_only_map"] and p["wilcoxon_p"] is not None
                            and p["wilcoxon_p"] < 0.05 and m["map"] >= m["count_only_map"])
    (HERE / "results" / "keyness3_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("choice", "fresh", "passes")}, indent=1))


if __name__ == "__main__":
    main()
