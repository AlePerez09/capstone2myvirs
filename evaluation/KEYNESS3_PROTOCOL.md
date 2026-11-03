# Relevance, third try: subject-aware relevance (written before scoring)

**MyVIRS Team A** · Written November 3, 2026, before any setting below was
scored. Follows `KEYNESS2_RESULTS.md`: keyness relevance clearly helped on
science books (Biology, Chemistry) and did not help on math books
(Trigonometry, Geometry, Algebra).

## Idea

Use relevance where the evidence says it helps. The ranking first decides,
from the text alone, whether a passage is math or science, then uses the
relevance setting that worked best for that kind of text. If counting
alone is best for math, math passages get no relevance.

## Math detector (no answer key involved)

math score of a passage = share of its non-space characters that are
digits or math symbols (`= + − × ÷ ^ √ π θ ∑ ∫ ° < > ≤ ≥ ±` and `/`). A passage
is math if its score is above a threshold. The threshold is the value that
best separates the lessons of the seen math books (Trigonometry, Basic
Geometry Concepts, Basic Algebra Concepts) from the seen science books
(Biology, Chemistry), using only which book each lesson is from.

## Settings (same 12 as the second try, plus "none")

Relevance score: `english` keyness (log ratio vs everyday English),
`textbooks` keyness (TF-IDF vs a textbook pile), or `both` (their average);
weight w in {0.25, 0.5, 0.75, 1.0}; or `none` (count only).
priority = (1 - w) x count percentile + w x relevance percentile. Filters
everywhere: stop words, layout words, generic verbs, number words dropped.

Textbook pile (1,500-word chunks): Life Science MS, People's Physics
Concepts, Calculus, Biology, Trigonometry (repaired), Chemistry, Basic
Geometry Concepts, Basic Algebra Concepts. A book's own chunks are left out
when ranking its lessons. Earth Science HS and Basic Probability and
Statistics Concepts are removed from the pile because they share a subject
with the new test books.

## Choosing (only on the five books already seen)

- Science setting: best average MAP over Biology and Chemistry.
- Math setting: best average MAP over Trigonometry, Geometry and Algebra
  (`none` allowed).
- Ties: smaller w. Nothing else is tried afterwards.

## Fresh test books (never scored or used in any pile)

- **CK-12 Earth Science MS** (science): Vocabulary = bullet list after the
  "Vocabulary" heading; lesson text = "Introduction" up to "Lesson Review
  Questions".
- **CK-12 Advanced Probability and Statistics Concepts** (math): same
  concepts format as Basic Geometry/Algebra Concepts.

Answer key: first word of each term, as before.

## Test (run once): subject-aware ranking vs count only, same filters

Wilcoxon signed-rank, two-sided, per-lesson average precision.
**Passes** only if: (1) pooled over both fresh books, MAP higher with
p < 0.05, and (2) on the fresh math book, MAP not lower than count only.
Also reported: each book alone, the official frequency-only baseline, how
many fresh lessons the detector labels math, and the result with the
detector replaced by the true book subject.

## Caveats stated in advance

- This is the third try at relevance today. The method is shaped by what
  the earlier tries showed on the five seen books; that is why the test
  uses two new books.
- If math passages get `none`, relevance only acts on science text, and the
  report will say so plainly.
- If it fails, it is reported as is, and there will be no fourth try today.
