# Evaluation Criterion — Sprint 4

**MyVIRS Team A** · Written October 26, 2026, before any Sprint 4 evaluation was run.
The commit date of this file is the record that the criterion came first.

## The question

Does combining relevance with frequency pick the words worth teaching
better than frequency alone?

In Sprint 3, relevance on its own lost to frequency on CK-12 Biology
(average precision 0.150 vs. 0.198, frequency better in 78 of 85 lessons).
This sprint tests the combined ranking, which is what MyVIRS actually uses.

## What we compare

| Ranking | What it is |
|---|---|
| **Frequency-only (baseline)** | `priority_ranking.py --frequency-only`: band score alone, ties broken by count |
| Relevance-only | TextRank percentile alone |
| **Combined (the one being tested)** | `priority_ranking.py`: 0.5 × band score + 0.5 × relevance |
| Combined + improvements | Combined, with the relevance options added this sprint (weighted links, textbook-verb filter, abbreviation grouping). Reported separately as exploratory. |

All rankings use the same pre-processing, word families, number handling
and stop word filtering, so the only difference is how words are scored.

**Fixed in advance:** the 0.5 / 0.5 weights and the band scores (HIGH 1.0,
MID 0.6, LOW 0.3, not listed 0.1). We will not change them after seeing
results. If we try other weights, that is exploratory: tune on Biology
only and report the math book as the held-out test.

**Word lists:** Eric's five lists if they are loaded before the evaluation
runs; otherwise the temporary `word_categories.json` bands, reported as a
limitation. Whichever is used is named in the results.

## Answer keys

**A. CK-12 lesson vocabulary (primary).** Each CK-12 lesson starts with a
Vocabulary list of its key terms. Each lesson is ranked as its own
passage, and its Vocabulary list is the answer key. The Vocabulary and
Glossary sections are removed from the text first, so no ranking sees
the answer. Answer-key words are mapped to word family headwords the same
way the text is, so "cells" in the key matches "cell" in the ranking.
Books: CK-12 Biology and at least one CK-12 math book that has lesson
Vocabulary lists (Trigonometry if it does, otherwise Algebra I or
Geometry).

**B. Eric's picks (secondary).** For 3 to 5 short passages, Eric marks the
ten words he would teach first. Used only if we receive them before the
evaluation runs.

## Metrics

- **Primary: mean average precision (MAP)** across lessons. It rewards
  putting key terms near the top of the list.
- Secondary: precision@10 and recall@10 per lesson.
- For Eric's passages: how many of his ten words each ranking puts in its top ten.

## Success bar

**Criterion met** if, on **both** books, the combined ranking has a higher
MAP than frequency-only **and** a Wilcoxon signed-rank test across lessons
gives p < 0.05.

- **Partly met:** combined beats frequency-only significantly on one book only.
- **Not met:** combined doesn't significantly beat frequency-only on either book.

Secondary check (if Eric's picks arrive): combined places more of his ten
words in its top ten than frequency-only in most of his passages.

We report the result whichever way it goes, including the per-lesson wins
and losses.

## Known limitations, stated in advance

- CK-12 Vocabulary lists are words the book repeats on purpose, which
  favors frequency. That is why Eric's picks are included as a second key.
- Only the first word of multiword terms is reliable in the answer key
  ("nitrogen" from "nitrogen cycle").
- The word list loader has only been tested on mock files until Eric's
  real files are loaded.
- Two textbooks, both CK-12, so results may not carry over to other
  publishers or subjects.
