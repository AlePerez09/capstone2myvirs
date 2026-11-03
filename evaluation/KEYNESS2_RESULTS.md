# Relevance, second try: results

**MyVIRS Team A** · Run November 3, 2026, following `KEYNESS2_PROTOCOL.md`
(committed before scoring, `7f7568c`). Scripts: `evaluation/fresh_books.py`,
`evaluation/test_keyness2.py`; numbers in `results/keyness2_test.json`.

## Verdict: relevance does NOT pass on fresh books

On three CK-12 books never used before, the chosen relevance setting is
slightly ahead of counting alone overall, but not significantly
(pooled MAP 0.424 vs 0.406, p = 0.10), and it ties on the two math books.
It clearly wins on Chemistry and loses (not significantly) on Geometry.

**What did hold up on fresh books:** counting words in the lesson with filler
filtered out (the Step 4 change) beats the official frequency-only ranking
on all three fresh books, in 90 to 101 of each book's lessons (p < 10^-12).

## Chosen on Biology + Trigonometry

12 pre-set settings; best average of the two books' MAPs was **`both`
(mean of English keyness and textbook keyness), weight 1.0**: Biology
0.420, Trigonometry 0.267, average 0.343 (count only: 0.231 / 0.293).
Textbook keyness alone did best on Trigonometry (0.380 at weight 0.25) but
had a lower average, so by the plan it was not chosen.

## Fresh books (run once)

MAP, (lessons better / worse than count only), Wilcoxon two-sided p.

| Fresh book | Frequency-only (official) | Count only | Chosen relevance | vs count only |
|---|---|---|---|---|
| Chemistry (109 lessons, science) | 0.238 | 0.319 | **0.381** | 66 / 37, p = 0.003 |
| Basic Geometry Concepts (119, math) | 0.395 | **0.557** | 0.521 | 43 / 66, p = 0.16 |
| Basic Algebra Concepts (134, math) | 0.217 | 0.343 | 0.371 | 76 / 50, p = 0.14 |
| Pooled, all fresh (362) | | 0.406 | 0.424 | 185 / 153, p = 0.10 |
| Pooled, math (253) | | 0.444 | 0.442 | 119 / 116, p = 0.97 |

Pass rule: pooled win with p < 0.05 **and** math not lower. Result: fails on
the first condition, borderline on the second.

## Step 4 setting on fresh books (extra check)

`RECOMMENDED` + drop_numbers (0.75 count + 0.25 TextRank, filler dropped)
vs the official frequency-only ranking (`results/fresh_books_counting_check.json`):
Chemistry 0.309 vs 0.238 (90 better / 8 worse), Geometry 0.566 vs 0.395
(101 / 4), Algebra 0.340 vs 0.217 (101 / 24); all p < 10^-12.

## What this means

- The robust improvement is in-lesson counting with filler filtered out. It
  now holds on five CK-12 books, three of them fresh.
- Relevance that measures "how specific is this word to this lesson" helps
  on science text (Biology, Chemistry, learner key) but not on math, where
  the vocabulary is ordinary words with special meanings.
- A subject-aware option (keyness for science, counting for math) is the
  obvious next idea, but it would need its own plan and fresh text again.

## Caveats

- First-word answer keys from CK-12 Vocabulary lists, which favor counting.
- Fresh books come from a public mirror of CK-12 PDFs; text extracted
  automatically.
