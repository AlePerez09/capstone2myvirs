"""
MyVIRS Team A, Sprint 3: combine frequency and relevance into one ranking.

First version by Fernando (frequency band + TextRank, frequency-only
fallback). Updated to follow Isa's integration layer design and to run on
the Sprint 3 pipeline (word families, percentile relevance).

For each word family in a text:

    priority = FREQUENCY_WEIGHT * band_score + RELEVANCE_WEIGHT * relevance

- band_score comes from the frequency band, plus a grade bonus (below).
  Common bands score higher, following Eric's approach of teaching the
  most frequent words first:
      HIGH 1.0, MID 0.6, LOW 0.3, not in any list 0.1
- relevance is the family's TextRank percentile within the text, 0 to 1,
  straight from pipeline.analyze_text(). It is 0 for families TextRank
  ran on but didn't score (function words, adverbs). Percentile is used
  instead of dividing by the top score so one standout word doesn't push
  everyone else toward zero.
- If relevance wasn't computed (frequency_only=True), priority is
  band_score alone. That is the frequency-only baseline.
- A family on the K-12 list at or below the text's grade gets +0.2 on its
  band_score, capped at 1.0.
- Ties break by how often the family appears in the text.

Frequency bands come from a "lexicon": {headword: {"band", "subject",
"grade_level", "frequency_count"}}. load_default_lexicon() reads Eric's
word lists (word_lists.py) when they're in data/word_lists/, and otherwise
falls back to word_categories.json (the ~2,300 words recovered from the
old site), which isn't a reliable frequency list.

Run:
    python3 priority_ranking.py "your passage here"
    python3 priority_ranking.py --text-file data/biology.txt --top 25
    python3 priority_ranking.py --text-file data/biology.txt --frequency-only
"""

import argparse
import json
from pathlib import Path

FREQUENCY_WEIGHT = 0.5
RELEVANCE_WEIGHT = 0.5
BAND_SCORES = {"HIGH": 1.0, "MID": 0.6, "LOW": 0.3, "NONE": 0.1}
GRADE_BONUS = 0.2
GRADES = ["K"] + [f"G{i}" for i in range(1, 13)]

CATEGORY_FILE = Path(__file__).parent / "word_categories.json"

# Textbook layout words: frequent, but not vocabulary to teach
LAYOUT_WORDS = {"figure", "page", "chapter", "lesson", "flexbook", "www"}

# Temporary mapping for word_categories.json. K1 and K2 are the 2,000 most
# frequent words, so they map to HIGH. AWL words are academic vocabulary
# outside that top 2,000, so they map to MID with subject "academic".
OLD_CATEGORY_MAP = {
    "K1": ("HIGH", "general"),
    "K2": ("HIGH", "general"),
    "BAW": ("MID", "academic"),
    "AWL": ("MID", "academic"),
}


def lexicon_from_word_categories(path=CATEGORY_FILE):
    """Temporary lexicon from the recovered word list. Replace with the
    loader for Eric's lists once it's in."""
    with open(path, encoding="utf-8") as f:
        categories = json.load(f)
    lexicon = {}
    for word, category in categories.items():
        band, subject = OLD_CATEGORY_MAP.get(category, ("NONE", "general"))
        lexicon[word.lower()] = {"band": band, "subject": subject,
                                 "grade_level": None, "frequency_count": None}
    return lexicon


def load_default_lexicon(verbose=True):
    """Eric's word lists if they're in data/word_lists/, otherwise the
    temporary list from word_categories.json."""
    import sys
    import word_lists

    if word_lists.files_present():
        return word_lists.load_lexicon()
    if verbose:
        print("(Eric's word lists not found in data/word_lists/, using the temporary "
              "word_categories.json bands)", file=sys.stderr)
    return lexicon_from_word_categories()


def lookup(record, lexicon):
    """Find a family in the lexicon by its headword, or failing that by any
    of its forms (the old list stores some words as forms, not headwords)."""
    for key in [record["headword"], *record.get("forms", [])]:
        if key in lexicon:
            return lexicon[key]
    return {"band": "NONE", "subject": "general", "grade_level": None,
            "frequency_count": None}


def band_score(entry, text_grade=None):
    score = BAND_SCORES.get(entry["band"], BAND_SCORES["NONE"])
    grade = entry.get("grade_level")
    if text_grade and grade in GRADES and text_grade in GRADES:
        if GRADES.index(grade) <= GRADES.index(text_grade):
            score = min(1.0, score + GRADE_BONUS)
    return score


def rank_records(records, lexicon, frequency_only=False, text_grade=None,
                 frequency_weight=FREQUENCY_WEIGHT, relevance_weight=RELEVANCE_WEIGHT):
    """Take pipeline.analyze_text() records and return them ranked, with
    band, subject, grade_level, priority and rank added. Rank 1 = teach first.
    Stop words and textbook layout words (figure, page) are left out,
    since they aren't vocabulary to teach."""
    from spacy.lang.en.stop_words import STOP_WORDS

    ranked = []
    for rec in records:
        head = rec["headword"]
        if rec.get("is_stop") or head in STOP_WORDS or head in LAYOUT_WORDS:
            continue
        entry = lookup(rec, lexicon)
        freq = band_score(entry, text_grade)
        if frequency_only:
            relevance = None
            priority = freq
        else:
            relevance = rec.get("relevance") or 0.0
            priority = frequency_weight * freq + relevance_weight * relevance
        ranked.append({
            **rec,
            "band": entry["band"],
            "subject": entry["subject"],
            "grade_level": entry["grade_level"],
            "frequency_count": entry["frequency_count"],
            "relevance": relevance,
            "priority": round(priority, 4),
        })
    ranked.sort(key=lambda r: (-r["priority"], -r["count"], r["headword"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return ranked


def rank_text(text, lexicon=None, frequency_only=False, text_grade=None):
    """Raw text in, ranked word families out."""
    import pipeline

    lexicon = lexicon if lexicon is not None else load_default_lexicon()
    records = pipeline.analyze_text(text)
    return rank_records(records, lexicon, frequency_only, text_grade)


def main():
    parser = argparse.ArgumentParser(description="MyVIRS combined ranking")
    parser.add_argument("text", nargs="*", help="passage to rank")
    parser.add_argument("--text-file", help="rank a saved .txt file")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--frequency-only", action="store_true",
                        help="ignore relevance (the frequency-only baseline)")
    parser.add_argument("--grade", help="text grade for the grade bonus, e.g. G7")
    args = parser.parse_args()

    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = " ".join(args.text) or (
            "The teacher asked the students to analyze the function of the ecosystem. "
            "Photosynthesis is the process by which plants convert light into energy."
        )

    ranked = rank_text(text, frequency_only=args.frequency_only, text_grade=args.grade)
    mode = "frequency only" if args.frequency_only else "frequency + relevance"
    print(f"Ranked {len(ranked)} word families ({mode})\n")
    print(f"{'rank':>4}  {'headword':<16}{'band':<6}{'relevance':>10}{'priority':>10}{'count':>8}")
    for r in ranked[: args.top]:
        rel = "-" if r["relevance"] is None else f"{r['relevance']:.2f}"
        print(f"{r['rank']:>4}  {r['headword']:<16}{r['band']:<6}{rel:>10}{r['priority']:>10.3f}{r['count']:>8}")


if __name__ == "__main__":
    main()
