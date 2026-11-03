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

Sprint 5 options (all off by default, so the Sprint 4 official setting
above is unchanged):
- score_by="count": the frequency part is the family's count within this
  text, as a percentile among the words kept (0 = rarest, 1 = most
  repeated), instead of its VIRS band. The Sprint 4 evaluation found the
  band is the weak part of the ranking: words the lesson repeats are much
  more often the ones to teach than words that are common in English.
- drop_generic_verbs=True: leave out generic textbook verbs (include, use,
  find, produce, occur...). These are pipeline.TEXTBOOK_VERBS plus a few
  more seen crowding the top 10 in the evaluation.
- drop_numbers=True: leave out spelled-out number words (one, two,
  forty...). Off by default: number words were requested as vocabulary.
- RECOMMENDED below is the setting picked in the Sprint 4 exploratory
  tuning: 0.75 x count percentile + 0.25 x relevance, generic verbs dropped.
- relevance="keyness": replace TextRank with keyness, how much more this
  text uses a word than everyday English does (wordfreq frequencies, summed
  over the family's forms). keyness_formula "tf_rarity" = count x
  -log10(English frequency); "log_ratio" = log(share of the text) -
  log(English frequency). Words wordfreq doesn't know (mostly extraction
  glitches) get no keyness. Needs `pip install wordfreq`. See
  evaluation/KEYNESS_PROTOCOL.md and KEYNESS_RESULTS.md.
- relevance="subject": subject-aware relevance, the setting that passed the
  third test (evaluation/KEYNESS3_PROTOCOL.md, KEYNESS3_RESULTS.md). The
  text is labeled math or science from its share of digits and math
  symbols. Science text: 0.25 x count + 0.75 x the average of keyness vs
  everyday English and keyness vs a pile of other textbooks. Math text:
  0.25 x count + 0.75 x keyness vs the textbook pile only (math words like
  "unit" or "identity" are common in English but not in other textbooks).
  The pile is data/reference_pile.json.gz. Use SUBJECT_AWARE, and pass the
  text (rank_text does this for you).

Frequency bands come from a "lexicon": {headword: {"band", "subject",
"grade_level", "frequency_count"}}. load_default_lexicon() reads Eric's
word lists (word_lists.py) when they're in data/word_lists/, and otherwise
falls back to the full VIRS list (data/virs_words.csv), then to
word_categories.json (an incomplete ~2,300-word piece of that list).

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

# Generic verbs seen crowding the top 10 in the Sprint 4 evaluation that
# pipeline.TEXTBOOK_VERBS doesn't cover. Matched on the headword.
EXTRA_GENERIC_VERBS = {"produce", "occur", "represent", "need", "help", "cause",
                       "form", "define", "determine", "contain", "allow", "become"}

# Setting chosen in the Sprint 4 exploratory tuning (tuned on Biology,
# checked on Trigonometry). Number words are NOT dropped here; pass
# drop_numbers=True separately if the team decides to.
RECOMMENDED = {"score_by": "count", "frequency_weight": 0.75,
               "relevance_weight": 0.25, "drop_generic_verbs": True}

# Subject-aware relevance, chosen on five CK-12 books and confirmed on two
# fresh ones (evaluation/KEYNESS3_RESULTS.md). Number words are KEPT (they
# were requested as vocabulary); the win holds with them kept too. Pass
# drop_numbers=True to leave them out, as in the original test.
SUBJECT_AWARE = {"score_by": "count", "frequency_weight": 0.25, "relevance_weight": 0.75,
                 "drop_generic_verbs": True, "drop_numbers": False, "relevance": "subject"}
MATH_CHARS = set("0123456789=+\u2212\u00d7\u00f7^\u221a\u03c0\u03b8\u2211\u222b\u00b0<>\u2264\u2265\u00b1/")
MATH_THRESHOLD = 0.0374  # set on the seen books, see KEYNESS3_RESULTS.md
REFERENCE_PILE = Path(__file__).parent / "data" / "reference_pile.json.gz"
_PILE = None

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
    """Pick the best word list available, in this order:
    1. Eric's five Excel files in data/word_lists/
    2. the full VIRS word list, data/virs_words.csv (~30,000 words)
    3. word_categories.json (the ~2,300-word partial list, last resort)"""
    import sys
    import word_lists

    if word_lists.files_present():
        return word_lists.load_lexicon()
    if word_lists.VIRS_CSV.exists():
        return word_lists.load_virs_csv()
    if verbose:
        print("(no full word list found, using the partial word_categories.json bands)",
              file=sys.stderr)
    return lexicon_from_word_categories()


def lookup(record, lexicon):
    """Find a family in the lexicon by its headword, or failing that by any
    of its forms (the old list stores some words as forms, not headwords)."""
    for key in [record["headword"], *record.get("forms", [])]:
        if key in lexicon:
            return lexicon[key]
    return {"band": "NONE", "subject": "general", "grade_level": None,
            "k_level": None, "frequency_count": None}


def band_score(entry, text_grade=None):
    score = BAND_SCORES.get(entry["band"], BAND_SCORES["NONE"])
    grade = entry.get("grade_level")
    if text_grade and grade in GRADES and text_grade in GRADES:
        if GRADES.index(grade) <= GRADES.index(text_grade):
            score = min(1.0, score + GRADE_BONUS)
    return score


def generic_verbs():
    from pipeline import TEXTBOOK_VERBS
    return set(TEXTBOOK_VERBS) | EXTRA_GENERIC_VERBS


def count_percentiles(counts):
    """Each count's percentile among all counts, 0 to 1. Equal counts share
    the average of their positions, so ties get the same score."""
    order = sorted(range(len(counts)), key=lambda i: counts[i])
    pct = [0.0] * len(counts)
    denom = max(len(counts) - 1, 1)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and counts[order[j + 1]] == counts[order[i]]:
            j += 1
        for k in range(i, j + 1):
            pct[order[k]] = (i + j) / 2 / denom
        i = j + 1
    return pct


def english_frequency(rec):
    """How often the family is used in everyday English: wordfreq frequency
    summed over the headword and its forms (0 if wordfreq doesn't know it)."""
    from wordfreq import word_frequency
    forms = {rec["headword"], *rec.get("forms", [])}
    return sum(word_frequency(f, "en") for f in forms)


def keyness_scores(records, formula="tf_rarity"):
    """Keyness of each record: how much more this text uses the word than
    everyday English does. Returned as percentiles within the text, 0 to 1.
    Words with no English frequency (glitches, names) score 0."""
    import math
    total = sum(r["count"] for r in records) or 1
    raw = []
    for r in records:
        freq = english_frequency(r)
        if freq <= 0:
            raw.append(None)
        elif formula == "tf_rarity":
            raw.append(r["count"] * -math.log10(freq))
        elif formula == "log_ratio":
            raw.append(math.log(r["count"] / total) - math.log(freq))
        else:
            raise ValueError(f"keyness_formula must be 'tf_rarity' or 'log_ratio', not {formula!r}")
    known = [i for i, x in enumerate(raw) if x is not None]
    pcts = count_percentiles([raw[i] for i in known])
    out = [0.0] * len(records)
    for i, p in zip(known, pcts):
        out[i] = p
    return out


def math_score(text):
    """Share of the text's non-space characters that are digits or math symbols."""
    chars = [c for c in text if not c.isspace()]
    return sum(c in MATH_CHARS for c in chars) / max(len(chars), 1)


def is_math(text):
    return math_score(text) > MATH_THRESHOLD


def load_pile():
    global _PILE
    if _PILE is None:
        import gzip
        with gzip.open(REFERENCE_PILE, "rt", encoding="utf-8") as f:
            data = json.load(f)
        _PILE = (data["chunks"], {w: set(ids) for w, ids in data["postings"].items()})
    return _PILE


def textbook_keyness(records, pile=None):
    """Keyness vs other textbooks: count x log((chunks + 1) / (chunks with any
    form of the word + 1)), as percentiles within the text."""
    import math
    n, postings = pile or load_pile()
    raw = []
    for r in records:
        hit = set()
        for f in {r["headword"], *r.get("forms", [])}:
            hit |= postings.get(f, set())
        raw.append(r["count"] * math.log((n + 1) / (len(hit) + 1)))
    return count_percentiles(raw)


def subject_relevance(records, text):
    """Subject-aware relevance (see the module docstring), 0 to 1 per record."""
    textbooks = textbook_keyness(records)
    if is_math(text):
        return textbooks
    english = keyness_scores(records, "log_ratio")
    return [(a + b) / 2 for a, b in zip(english, textbooks)]


def rank_records(records, lexicon, frequency_only=False, text_grade=None,
                 frequency_weight=FREQUENCY_WEIGHT, relevance_weight=RELEVANCE_WEIGHT,
                 score_by="band", drop_numbers=False, drop_generic_verbs=False,
                 relevance="textrank", keyness_formula="tf_rarity", text=None):
    """Take pipeline.analyze_text() records and return them ranked, with
    band, subject, grade_level, priority and rank added. Rank 1 = teach first.
    Stop words and textbook layout words (figure, page) are left out,
    since they aren't vocabulary to teach.

    score_by: "band" (VIRS band score, the Sprint 4 official setting) or
    "count" (count percentile within this text). drop_numbers and
    drop_generic_verbs leave those words out. relevance: "textrank" (the
    pipeline's score), "keyness" (see keyness_scores) or "subject"
    (subject-aware, needs text=the passage). See the module docstring."""
    from spacy.lang.en.stop_words import STOP_WORDS
    from pipeline import NUMBER_WORDS

    if score_by not in ("band", "count"):
        raise ValueError(f"score_by must be 'band' or 'count', not {score_by!r}")
    verbs = generic_verbs() if drop_generic_verbs else set()
    kept = []
    for rec in records:
        head = rec["headword"]
        if head in NUMBER_WORDS:
            if drop_numbers:
                continue
            # otherwise numbers are kept even though spaCy calls them stop words
        elif rec.get("is_stop") or head in STOP_WORDS or head in LAYOUT_WORDS:
            continue
        if head in verbs:
            continue
        kept.append(rec)
    if score_by == "count":
        pcts = count_percentiles([rec["count"] for rec in kept])
    if relevance == "keyness":
        keys = keyness_scores(kept, keyness_formula)
    elif relevance == "subject":
        if text is None:
            raise ValueError("relevance='subject' needs text= (the passage), to tell math from science")
        keys = subject_relevance(kept, text)
    elif relevance != "textrank":
        raise ValueError(f"relevance must be 'textrank', 'keyness' or 'subject', not {relevance!r}")

    ranked = []
    for i, rec in enumerate(kept):
        entry = lookup(rec, lexicon)
        freq = pcts[i] if score_by == "count" else band_score(entry, text_grade)
        if frequency_only:
            rel = None
            priority = freq
        else:
            rel = keys[i] if relevance in ("keyness", "subject") else (rec.get("relevance") or 0.0)
            priority = frequency_weight * freq + relevance_weight * rel
        ranked.append({
            **rec,
            "band": entry["band"],
            "subject": entry["subject"],
            "grade_level": entry["grade_level"],
            "k_level": entry.get("k_level"),
            "frequency_count": entry["frequency_count"],
            "relevance": rel,
            "frequency_score": round(freq, 4),
            "priority": round(priority, 4),
        })
    ranked.sort(key=lambda r: (-r["priority"], -r["count"], r["headword"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return ranked


def rank_text(text, lexicon=None, frequency_only=False, text_grade=None, **options):
    """Raw text in, ranked word families out. options go to rank_records()
    (score_by, drop_numbers, drop_generic_verbs, the weights); for example
    rank_text(text, **RECOMMENDED)."""
    import pipeline

    lexicon = lexicon if lexicon is not None else load_default_lexicon()
    records = pipeline.analyze_text(text)
    if options.get("relevance") == "subject":
        options.setdefault("text", text)
    return rank_records(records, lexicon, frequency_only, text_grade, **options)


def main():
    parser = argparse.ArgumentParser(description="MyVIRS combined ranking")
    parser.add_argument("text", nargs="*", help="passage to rank")
    parser.add_argument("--text-file", help="rank a saved .txt file")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--frequency-only", action="store_true",
                        help="ignore relevance (the frequency-only baseline)")
    parser.add_argument("--grade", help="text grade for the grade bonus, e.g. G7")
    parser.add_argument("--score-by", choices=["band", "count"], default=None,
                        help="frequency part: VIRS band (default) or count within the text")
    parser.add_argument("--drop-numbers", action="store_true",
                        help="leave out spelled-out number words (one, two, forty...)")
    parser.add_argument("--drop-generic-verbs", action="store_true",
                        help="leave out generic verbs (include, use, find, produce, occur...)")
    parser.add_argument("--frequency-weight", type=float, default=None)
    parser.add_argument("--relevance-weight", type=float, default=None)
    parser.add_argument("--subject-aware", action="store_true",
                        help="subject-aware relevance (SUBJECT_AWARE), the setting that passed the "
                             "third relevance test; keeps number words unless --drop-numbers")
    parser.add_argument("--relevance", choices=["textrank", "keyness", "subject"], default=None,
                        help="relevance score: TextRank (default) or keyness vs everyday English")
    parser.add_argument("--keyness-formula", choices=["tf_rarity", "log_ratio"], default=None)
    parser.add_argument("--recommended", action="store_true",
                        help="Sprint 4 tuned setting: 0.75 x count + 0.25 x relevance, "
                             "generic verbs dropped (numbers kept unless --drop-numbers)")
    args = parser.parse_args()

    options = dict(RECOMMENDED) if args.recommended else {}
    if args.subject_aware:
        options = dict(SUBJECT_AWARE)
    if args.score_by:
        options["score_by"] = args.score_by
    if args.drop_numbers:
        options["drop_numbers"] = True
    if args.drop_generic_verbs:
        options["drop_generic_verbs"] = True
    if args.frequency_weight is not None:
        options["frequency_weight"] = args.frequency_weight
    if args.relevance_weight is not None:
        options["relevance_weight"] = args.relevance_weight
    if args.relevance:
        options["relevance"] = args.relevance
    if args.keyness_formula:
        options["keyness_formula"] = args.keyness_formula

    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = " ".join(args.text) or (
            "The teacher asked the students to analyze the function of the ecosystem. "
            "Photosynthesis is the process by which plants convert light into energy."
        )

    ranked = rank_text(text, frequency_only=args.frequency_only, text_grade=args.grade,
                       **options)
    mode = "frequency only" if args.frequency_only else "frequency + relevance"
    mode += ", count in text" if options.get("score_by") == "count" else ", VIRS band"
    print(f"Ranked {len(ranked)} word families ({mode})\n")
    print(f"{'rank':>4}  {'headword':<16}{'band':<6}{'relevance':>10}{'priority':>10}{'count':>8}")
    for r in ranked[: args.top]:
        rel = "-" if r["relevance"] is None else f"{r['relevance']:.2f}"
        print(f"{r['rank']:>4}  {r['headword']:<16}{r['band']:<6}{rel:>10}{r['priority']:>10.3f}{r['count']:>8}")


if __name__ == "__main__":
    main()
