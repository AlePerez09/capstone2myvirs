"""
MyVIRS Sprint 2 — priority ranking.

Merges each headword's frequency band (word_categories.json) with its
TextRank relevance score (textrank.py) into one priority score, so the
words most worth teaching come first.

    priority = FREQUENCY_WEIGHT * band_score + RELEVANCE_WEIGHT * relevance

- band_score: 0-1, higher for words learners are less likely to know
  (K1 lowest, academic/uncategorized highest). See BAND_SCORES.
- relevance: TextRank score divided by the passage maximum, so 0-1.
- If no relevance scores are available (empty/None), priority is the
  band score alone.
- A headword missing from a non-empty relevance dict gets relevance 0.

Run:  python3 priority_ranking.py "your passage here"
"""

from walking_skeleton import CATEGORY_FILE, load_word_categories, tokenize

BAND_SCORES = {
    "K1": 0.1,
    "K2": 0.4,
    "BAW": 0.7,
    "AWL": 0.9,
    "UNKNOWN": 1.0,
}
FREQUENCY_WEIGHT = 0.5
RELEVANCE_WEIGHT = 0.5


def band_score(word, categories):
    return BAND_SCORES.get(categories.get(word.lower(), "UNKNOWN"), BAND_SCORES["UNKNOWN"])


def rank_headwords(headwords, categories, relevance=None,
                   frequency_weight=FREQUENCY_WEIGHT, relevance_weight=RELEVANCE_WEIGHT):
    """Return a list of dicts sorted by descending priority.

    headwords: iterable of words (duplicates and case are collapsed).
    categories: word -> band dict (word_categories.json).
    relevance: word -> TextRank score dict, or None/empty for frequency-only.
    Every headword gets a priority; ties break alphabetically.
    """
    words = sorted({w.lower() for w in headwords})
    rel = {w.lower(): s for w, s in (relevance or {}).items()}
    max_rel = max(rel.values(), default=0)
    use_relevance = max_rel > 0

    ranked = []
    for word in words:
        band = categories.get(word, "UNKNOWN")
        freq = band_score(word, categories)
        if use_relevance:
            rel_norm = rel.get(word, 0.0) / max_rel
            priority = frequency_weight * freq + relevance_weight * rel_norm
        else:
            rel_norm = None
            priority = freq
        ranked.append({
            "word": word,
            "band": band,
            "relevance_score": rel.get(word) if use_relevance else None,
            "priority": round(priority, 4),
            "source": "frequency+relevance" if use_relevance else "frequency-only",
        })
    ranked.sort(key=lambda r: (-r["priority"], r["word"]))
    return ranked


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The teacher asked the students to analyze the function of the ecosystem. "
        "Photosynthesis is the process by which plants convert light into energy."
    )
    cats = load_word_categories(CATEGORY_FILE)
    rel = None
    try:
        from textrank import TextRank
        tr = TextRank()
        tr.analyze(text, lower=True)
        rel = tr.node_weight
    except Exception as e:  # spaCy/model missing -> frequency-only
        print(f"(relevance unavailable, using frequency only: {e})")
    for r in rank_headwords(tokenize(text), cats, rel):
        print(f"  {r['word']:<15} {r['band']:<8} {r['priority']:.4f}  {r['source']}")
