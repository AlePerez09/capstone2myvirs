"""
Check that priority_ranking.SUBJECT_AWARE (the shipped code and the shipped
data/reference_pile.json.gz) reproduces the third relevance test on the two
fresh books (KEYNESS3_RESULTS.md), with number words dropped (as tested)
and kept (the default).

    python3 evaluation/check_subject_aware.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_evaluation as ev  # noqa: E402
import pipeline  # noqa: E402
import priority_ranking as pr  # noqa: E402
from test_keyness2 import test  # noqa: E402

def count_only(drop_numbers):
    return dict(score_by="count", drop_generic_verbs=True, drop_numbers=drop_numbers,
                frequency_weight=1.0, relevance_weight=0.0)


def main():
    lexicon = pr.load_default_lexicon(verbose=False)
    out = {}
    for drop in (True, False):
        label = "numbers dropped (as tested)" if drop else "numbers kept (SUBJECT_AWARE default)"
        out[label] = {}
        for name in ["earth_science", "prob_stats"]:
            lessons = json.loads((HERE / "data" / "fresh" / f"{name}_lessons.json").read_text(encoding="utf-8"))
            s, c, f = [], [], []
            for l in lessons:
                records = pipeline.analyze_text(l["text"])
                gold = ev.gold_set(l["first_words"], ev.word_to_head(records))
                if not gold:
                    continue
                subject = dict(pr.SUBJECT_AWARE, drop_numbers=drop, text=l["text"])
                for lst, opts in ((s, subject), (c, count_only(drop)), (f, dict(frequency_only=True))):
                    lst.append(ev.average_precision(
                        [r["headword"] for r in pr.rank_records(records, lexicon, **opts)], gold))
            out[label][name] = {**test(s, c), "frequency_only_map": round(float(np.mean(f)), 4)}
            print(label, name, out[label][name], flush=True)
    (HERE / "results" / "subject_aware_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
