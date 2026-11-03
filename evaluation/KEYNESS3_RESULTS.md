# Relevance, third try: subject-aware relevance — results

**MyVIRS Team A** · Run November 3, 2026, following `KEYNESS3_PROTOCOL.md`
(committed before scoring, `90d0768`). Scripts: `fresh_books.py`,
`test_keyness3.py`; numbers in `results/keyness3_test.json`.

## Verdict: PASSES on two fresh books

On two CK-12 books never used before, subject-aware relevance beats
counting alone on both, and clearly:

| Fresh book | Frequency-only (official) | Count only | **Count + subject-aware relevance** | Better / worse lessons | Wilcoxon p |
|---|---|---|---|---|---|
| Earth Science MS (81 lessons, science) | 0.234 | 0.312 | **0.409** | 60 / 21 | 0.00001 |
| Adv. Probability & Statistics Concepts (51, math) | 0.189 | 0.284 | **0.377** | 36 / 12 | 0.00009 |
| Both, pooled (132) | | 0.301 | **0.396** | 96 / 33 | < 0.001 |

Both pass conditions hold: pooled win with p < 0.05, and the math book is
not lower (it is higher). Using the true book subject instead of the
detector gives the same picture (Earth Science 0.414, Prob & Stats 0.355).

So on these books relevance itself is the reason for the gain: the
comparison holds counting and the filters fixed and only adds relevance.

## With number words kept (the default, since numbers were requested)

The test above dropped number words in both arms, as planned. Number words
are supposed to stay, so `SUBJECT_AWARE` now keeps them. Re-run on the same
fresh books with number words kept in both arms (a check after the planned
test, same settings, nothing re-tuned):

| Fresh book | Frequency-only | Count only | **Count + subject-aware relevance** | Better / worse | Wilcoxon p |
|---|---|---|---|---|---|
| Earth Science MS (81) | 0.234 | 0.295 | **0.395** | 61 / 20 | 0.000003 |
| Adv. Probability & Statistics (51, math) | 0.189 | 0.201 | **0.298** | 40 / 9 | 0.00002 |

Relevance still wins clearly on both. Numbers lower all math scores (the
CK-12 lists never contain number words), but relevance's gain over count only
is the same size.

## What was chosen (on the five seen books only)

- **Math detector:** a passage is math if more than 3.74% of its
  non-space characters are digits or math symbols. This separated seen
  math and science lessons with 83% accuracy. On the fresh books it
  labeled 4 of 81 Earth Science lessons and 37 of 51 Prob & Stats
  lessons as math.
- **Science text:** 0.25 x count + 0.75 x the average of keyness vs
  everyday English and keyness vs the textbook pile (Biology 0.393,
  Chemistry 0.408; count only 0.231, 0.319).
- **Math text:** 0.25 x count + 0.75 x keyness vs the textbook pile (Trig
  0.381, Geometry 0.617, Algebra 0.377; count only 0.293, 0.557, 0.343).

Why math works now: keyness against *other textbooks* (not everyday
English) doesn't punish *unit* or *identity*, which are common in English
but not on a typical textbook page. In the second try the pile had little
math in it; this pile includes the seen math books, and a math book's own
pages are always left out when ranking it.

## Built into the code

`priority_ranking.py`: `relevance="subject"` and the `SUBJECT_AWARE` preset
(`--subject-aware` on the command line; keeps number words, add
`--drop-numbers` to leave them out), with the pile shipped as
`data/reference_pile.json.gz` (400 KB). `evaluation/check_subject_aware.py`
re-runs the fresh books with the shipped code and data and gets exactly the
numbers above, both with numbers dropped and kept (`results/subject_aware_check.json`). Tests:
`tests/test_priority_ranking.py`.

Extra check, learner-focused key (13 Biology passages, all labeled science):
0.755 vs 0.642 for count only, 12 better / 1 worse, p < 0.001.

## Caveats

- This is the third relevance try today. The method was shaped by the first
  two tries on the five seen books; the two fresh books are what makes the
  result trustworthy, and they were scored once.
- Two fresh books, 132 lessons; answer keys are CK-12 Vocabulary first words.
- The planned test dropped number words; the numbers-kept result above is
  a check run afterwards on the same books.
- The pile and the fresh books are CK-12 PDFs from a public mirror
  (github.com/smile-pi/ck12_textbooks), text extracted automatically.
