"""
MyVIRS Team A, Sprint 4: the evaluation described in evaluation_criterion.md.

Question: does the combined ranking (priority_ranking.py, 0.5 x band score
+ 0.5 x relevance) pick the words worth teaching better than frequency
alone (priority_ranking.py --frequency-only)?

Built on Isa's Sprint 3 script (baseline-comparison/compare_baseline.py):
same idea, each CK-12 lesson is ranked as its own passage and its
Vocabulary list is the answer key, with the Vocabulary and Glossary
sections removed from the text so no ranking sees the answer.

Rankings (all from the same pipeline.analyze_text() records and the same
priority_ranking.rank_records() filtering, so the only difference is the
score):
  frequency_only     rank_records(frequency_only=True): band score, ties by
                     count. THE BASELINE.
  combined           rank_records(): 0.5 x band + 0.5 x relevance. TESTED.
  relevance_only     rank_records() with weights 0 / 1 (TextRank percentile).
  count_only         family count in the lesson (reference only; the Sprint 3
                     "frequency" baseline).
  combined_improved  combined on analyze_text(weighted=True, filter_verbs=True,
                     group_abbreviations=True), Fernando's Sprint 4 options.
                     Exploratory.
  combined_weighted / combined_verbs / combined_abbrev
                     each of Fernando's options on its own. Exploratory.

Answer key: the first word of each Vocabulary term (the only part the
Sprint 3 parser can read reliably), mapped to its word family headword the
same way the lesson text is.
  - Biology: parsed from data/biology.txt with compare_baseline.split_book.
  - Trigonometry: hand-transcribed in evaluation/data/trigonometry_vocab_key.json
    (the layout varies too much to parse), on the re-spaced text from
    evaluation/repair_spacing.py. A second Trigonometry key using every
    word of each term is reported as a sensitivity check.

Metrics per lesson: average precision, precision@10, recall@10.
Summary: MAP, mean P@10, Wilcoxon signed-rank (two-sided) across lessons.

Usage:
    python3 evaluation/run_evaluation.py --out evaluation/results
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path[:0] = [str(REPO), str(REPO / "baseline-comparison")]

import pipeline  # noqa: E402  (loads spaCy)
import priority_ranking  # noqa: E402
from compare_baseline import split_book, precision_at, recall_at, average_precision  # noqa: E402

PRIMARY = ["frequency_only", "combined", "relevance_only", "count_only"]
EXTRA = ["combined_improved", "combined_weighted", "combined_verbs", "combined_abbrev"]
METHODS = PRIMARY + EXTRA
IMPROVEMENTS = {
    "combined_improved": dict(weighted=True, filter_verbs=True, group_abbreviations=True),
    "combined_weighted": dict(weighted=True),
    "combined_verbs": dict(filter_verbs=True),
    "combined_abbrev": dict(group_abbreviations=True),
}
# First words that carry no meaning on their own ("non-included angle")
SKIP_FIRST = {"non", "one"}
STOP_TERM_WORDS = {"of", "a", "the", "to", "and", "an"}


# ---------- Books ----------

def biology_lessons(path):
    text = Path(path).read_text(encoding="utf-8")
    segments, _glossary = split_book(text)  # glossary is cut off the end
    # Lesson title: the last "N.N Title" heading before each Vocabulary block
    lines = text.split("\n")
    titles, last = [], ""
    for l in lines:
        if re.match(r"^\d+\.\d+ [A-Z]", l.strip()):
            last = l.strip()
        elif l.strip() == "Vocabulary":
            titles.append(last)
    lessons = []
    for idx, (vocab, seg_text) in enumerate(segments):
        if vocab:
            # segment idx follows the idx-th Vocabulary block, i.e. lesson idx
            title = titles[idx - 1] if 0 < idx <= len(titles) else ""  # segment idx follows block idx-1
            lessons.append({"id": f"bio-{idx}", "text": seg_text,
                            "terms": vocab, "first_words": vocab, "title": title[:60]})
    return lessons


def term_first_word(term):
    words = [w for w in re.split(r"[\s\-']+", term.lower()) if w.isalpha() and len(w) > 2]
    for w in words:
        if w not in SKIP_FIRST:
            return w
    return words[0] if words else None


def term_all_words(term):
    return [w for w in re.split(r"[\s\-']+", term.lower())
            if w.isalpha() and len(w) > 1 and w not in STOP_TERM_WORDS]


def trig_lessons(text_path, key_path):
    lines = Path(text_path).read_text(encoding="utf-8").split("\n")
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    starts = [i for i, l in enumerate(lines) if re.match(r"Learning [Oo]bjectives", l.strip())]
    lessons = []
    for block in key["blocks"]:
        v = block["line"] - 1
        assert lines[v].strip() == "Vocabulary", f"line {block['line']} is not a Vocabulary heading"
        start = max(s for s in starts if s < v) - 1  # include the lesson title line
        lessons.append({
            "id": f"trig-{block['line']}",
            "text": "\n".join(lines[start:v]),  # stops before the Vocabulary block
            "terms": block["terms"],
            "first_words": [w for w in map(term_first_word, block["terms"]) if w],
            "all_words": sorted({w for t in block["terms"] for w in term_all_words(t)}),
            "title": lines[start].strip()[:60],
        })
    return lessons


# ---------- Rankings ----------

def word_to_head(records):
    m = {}
    for r in records:
        for f in r.get("forms", []):
            m[f] = r["headword"]
        m.setdefault(r["headword"], r["headword"])
    return m


def rank_lesson(text, lexicon):
    records = pipeline.analyze_text(text)
    rr = priority_ranking.rank_records
    out = {
        "frequency_only": rr(records, lexicon, frequency_only=True),
        "combined": rr(records, lexicon),
        "relevance_only": rr(records, lexicon, frequency_weight=0.0, relevance_weight=1.0),
    }
    by_count = sorted(out["combined"], key=lambda r: (-r["count"], r["headword"]))
    out["count_only"] = by_count
    for name, opts in IMPROVEMENTS.items():
        out[name] = rr(pipeline.analyze_text(text, **opts), lexicon)
    heads = {m: [r["headword"] for r in rows] for m, rows in out.items()}
    detail = {r["headword"]: r for r in out["combined"]}
    return records, heads, detail


def gold_set(words, w2h, abbrev=False):
    gold = set()
    for w in words:
        if abbrev and w in pipeline.ABBREVIATIONS:
            w = pipeline.ABBREVIATIONS[w]
        if w in w2h:
            gold.add(w2h[w])
    return gold


# ---------- Stats ----------

def paired(rows, a, b, metric):
    x = [r[f"{a}_{metric}"] for r in rows]
    y = [r[f"{b}_{metric}"] for r in rows]
    try:
        p = float(wilcoxon(x, y).pvalue)
        p_greater = float(wilcoxon(x, y, alternative="greater").pvalue)
    except ValueError:  # all differences zero
        p = p_greater = None
    return {"mean_a": float(np.mean(x)), "mean_b": float(np.mean(y)),
            "better": sum(i > j for i, j in zip(x, y)),
            "worse": sum(i < j for i, j in zip(x, y)),
            "tied": sum(i == j for i, j in zip(x, y)),
            "wilcoxon_p_two_sided": p, "wilcoxon_p_combined_greater": p_greater}


def evaluate_book(name, lessons, lexicon, keys):
    rows = {k: [] for k in keys}
    loss_words = {k: {"gold_dropped": Counter(), "nongold_added": Counter()} for k in keys}
    top10 = []
    for lesson in lessons:
        records, heads, detail = rank_lesson(lesson["text"], lexicon)
        w2h = word_to_head(records)
        tops = {m: heads[m][:10] for m in METHODS}
        entry = {"lesson": lesson["id"], "title": lesson["title"], "terms": lesson["terms"],
                 "top10": tops}
        for k in keys:
            gold = gold_set(lesson[k], w2h)
            if not gold:
                continue
            row = {"lesson": lesson["id"], "title": lesson["title"], "gold": len(gold),
                   "families": len(heads["combined"])}
            for m in METHODS:
                g = gold
                if m in ("combined_improved", "combined_abbrev"):
                    g = gold_set(lesson[k], w2h, abbrev=True) | gold
                row[f"{m}_ap"] = average_precision(heads[m], g)
                row[f"{m}_p@10"] = precision_at(heads[m], g, 10)
                row[f"{m}_r@10"] = recall_at(heads[m], g, 10)
            rows[k].append(row)
            entry[f"gold_{k}"] = sorted(gold)
            # Where combined loses its top-10 places relative to frequency-only
            c10, f10 = set(tops["combined"]), set(tops["frequency_only"])
            for w in f10 - c10:
                if w in gold:
                    loss_words[k]["gold_dropped"][w] += 1
            for w in c10 - f10:
                if w not in gold:
                    d = detail.get(w, {})
                    loss_words[k]["nongold_added"][(w, d.get("band"))] += 1
        top10.append(entry)
        r0 = rows[keys[0]][-1] if rows[keys[0]] and rows[keys[0]][-1]["lesson"] == lesson["id"] else None
        if r0:
            print(f"{name} {lesson['id']:>12} gold={r0['gold']:>2} "
                  + " ".join(f"{m[:10]}={r0[m + '_ap']:.3f}" for m in PRIMARY + ["combined_improved"]),
                  flush=True)

    summary = {}
    for k in keys:
        rs = rows[k]
        s = {"lessons": len(rs)}
        for m in METHODS:
            for metric in ["ap", "p@10", "r@10"]:
                s[f"{m}_{'map' if metric == 'ap' else metric}"] = float(np.mean([r[f"{m}_{metric}"] for r in rs]))
        s["tests"] = {}
        for a, b in [("combined", "frequency_only"), ("combined_improved", "frequency_only"),
                     ("combined_improved", "combined"), ("relevance_only", "frequency_only"),
                     ("combined", "count_only"), ("combined_weighted", "combined"),
                     ("combined_verbs", "combined"), ("combined_abbrev", "combined")]:
            for metric in ["ap", "p@10"]:
                s["tests"][f"{a}_vs_{b}_{metric}"] = paired(rs, a, b, metric)
        t = s["tests"]["combined_vs_frequency_only_ap"]
        s["combined_beats_frequency_only"] = bool(
            t["mean_a"] > t["mean_b"] and t["wilcoxon_p_two_sided"] is not None
            and t["wilcoxon_p_two_sided"] < 0.05)
        s["losses"] = sorted(
            [{"lesson": r["lesson"], "title": r["title"],
              "combined_ap": round(r["combined_ap"], 4),
              "frequency_only_ap": round(r["frequency_only_ap"], 4)}
             for r in rs if r["combined_ap"] < r["frequency_only_ap"]],
            key=lambda d: d["combined_ap"] - d["frequency_only_ap"])
        s["gold_words_frequency_had_in_top10_but_combined_dropped"] = \
            loss_words[k]["gold_dropped"].most_common(25)
        s["non_key_words_combined_added_to_top10"] = [
            [w, band, n] for (w, band), n in loss_words[k]["nongold_added"].most_common(25)]
        summary[k] = s
    return rows, summary, top10


def write_csv(path, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(f"{r[c]:.4f}" if isinstance(r[c], float)
                             else '"' + str(r[c]).replace('"', "'") + '"' if isinstance(r[c], str)
                             else str(r[c]) for c in cols) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results"))
    ap.add_argument("--biology", default=str(REPO / "data" / "biology.txt"))
    ap.add_argument("--trig", default=str(HERE / "data" / "trigonometry_spaced.txt"))
    ap.add_argument("--trig-key", default=str(HERE / "data" / "trigonometry_vocab_key.json"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    lexicon = priority_ranking.load_default_lexicon()
    import word_lists
    source = ("Eric's five Excel lists" if word_lists.files_present()
              else "full VIRS list (data/virs_words.csv)" if word_lists.VIRS_CSV.exists()
              else "temporary word_categories.json")
    print(f"word list: {source}, {len(lexicon)} entries", flush=True)

    books = {
        "biology": (biology_lessons(args.biology), ["first_words"]),
        "trigonometry": (trig_lessons(args.trig, args.trig_key), ["first_words", "all_words"]),
    }
    results = {"word_list": source, "word_list_entries": len(lexicon),
               "band_counts": dict(Counter(e["band"] for e in lexicon.values())), "books": {}}
    for name, (lessons, keys) in books.items():
        rows, summary, top10 = evaluate_book(name, lessons, lexicon, keys)
        results["books"][name] = summary
        for k in keys:
            write_csv(os.path.join(args.out, f"{name}_{k}_lessons.csv"), rows[k])
        with open(os.path.join(args.out, f"{name}_top10.json"), "w", encoding="utf-8") as f:
            json.dump(top10, f, indent=1)

    met = [b for b in ("biology", "trigonometry")
           if results["books"][b]["first_words"]["combined_beats_frequency_only"]]
    results["verdict"] = {2: "met", 1: "partly met", 0: "not met"}[len(met)]
    results["books_where_combined_won_significantly"] = met
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({b: {k: {m: round(v, 3) for m, v in s.items() if m.endswith(("_map", "_p@10"))}
                          for k, s in bs.items()} for b, bs in results["books"].items()}, indent=1))
    print("verdict:", results["verdict"])


if __name__ == "__main__":
    main()
