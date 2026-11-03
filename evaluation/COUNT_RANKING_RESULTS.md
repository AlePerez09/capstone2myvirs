# Sprint 5: in-lesson counting and filler filtering

**MyVIRS Team A** · Run November 3, 2026 on repo commit `7ca7cf6` plus this
change. Follows up the Sprint 4 exploratory tuning (`RESULTS.md`).

## What changed

`priority_ranking.py` only (`pipeline.py` is untouched). Three new options
on `rank_records()` / `rank_text()` and the command line, **all off by
default**, so the Sprint 4 official setting and its results are unchanged
(checked: identical rankings with default options).

| Option | What it does |
|---|---|
| `score_by="count"` / `--score-by count` | Frequency part = the word's count in this text as a percentile (0 rarest, 1 most repeated), instead of its VIRS band |
| `drop_generic_verbs=True` / `--drop-generic-verbs` | Leaves out `pipeline.TEXTBOOK_VERBS` plus produce, occur, represent, need, help, cause, form, define, determine, contain, allow, become |
| `drop_numbers=True` / `--drop-numbers` | Leaves out spelled-out number words. Off by default and **not** in `RECOMMENDED`: number words were requested, so the team decides |
| `RECOMMENDED` / `--recommended` | The Sprint 4 tuned setting: 0.75 x count + 0.25 x relevance, generic verbs dropped |

Each ranked record also gets `frequency_score` (the frequency part used).
Tests: `tests/test_priority_ranking.py`.

```bash
python3 priority_ranking.py --text-file data/biology.txt --recommended
python3 priority_ranking.py --text-file data/biology.txt --recommended --drop-numbers
```

## Does it beat frequency-only?

`evaluation/check_count_ranking.py` runs the real `rank_records()` code on
the same lessons and answer keys as `run_evaluation.py`, against the
official frequency-only baseline. MAP, (lessons better / worse), Wilcoxon p.

| Setting | Biology (84) | Trigonometry (22) | Learner key (13) |
|---|---|---|---|
| Frequency-only (official baseline) | 0.164 | 0.193 | 0.538 |
| Combined, official (0.5 band + 0.5 relevance) | 0.143 (31/53, p<0.001) | 0.162 (7/15, p=0.09) | 0.533 (5/8, p=0.59) |
| **Recommended, numbers kept** | **0.209** (72/11, p<0.001) | 0.220 (12/9, p=0.41) | **0.645** (11/2, p=0.01) |
| **Recommended, numbers dropped** | **0.221** (75/9, p<0.001) | **0.277** (19/3, p=0.007) | **0.654** (12/1, p=0.002) |
| Count only, generic verbs dropped | 0.219 (76/7) | 0.222 (13/6, p=0.33) | 0.637 (11/2) |
| Count only, verbs + numbers dropped | 0.231 (80/4) | 0.293 (21/0, p<0.001) | 0.642 (11/2) |

- The recommended setting beats frequency-only on all three keys **if
  number words are dropped**. With number words kept (today's default),
  it still clearly wins on Biology and the learner key, but on
  Trigonometry the gain (0.220 vs 0.193) is not significant: in the math
  book, number words (three, four, forty) crowd the top 10.
- Relevance (TextRank) still adds nothing on CK-12 lists: count only is
  slightly better on both books (Biology significantly). On the learner
  key, relevance helps a little (0.654 vs 0.642, 8 better / 5 worse,
  p=0.46, not significant).
- Biology is where these settings were tuned, so its numbers are
  in-sample. Trigonometry and the learner key were not used for tuning.
- Trigonometry baseline is 0.193 here vs 0.192 in `RESULTS.md` (rounding /
  package version); everything else matches the Sprint 4 exploratory run.

## Exploratory: a different relevance signal

`evaluation/explore_keyness.py` (not pre-registered, one idea, three blend
weights, nothing tuned on a key). It replaces TextRank with "keyness": how
much more the lesson uses a word than expected from how common the word is
elsewhere. Verbs and numbers dropped in all rows.

| MAP | Biology | Trigonometry | Learner key |
|---|---|---|---|
| Count only | 0.231 | 0.293 | 0.642 |
| 0.75 count + 0.25 TextRank (recommended) | 0.221 | 0.277 | 0.654 |
| Keyness vs everyday English only | 0.298 | 0.341 | **0.719** |
| 0.5 count + 0.5 keyness vs English | 0.258 | 0.329 | 0.708 |
| Keyness vs other lessons in the book (TF-IDF) only | **0.367** | **0.453** | 0.671 |
| 0.5 count + 0.5 keyness vs book | 0.300 | 0.404 | 0.709 |

- Keyness vs everyday English (count in lesson x rarity in the `wordfreq`
  English word frequencies) needs no corpus of our own, so it works on one
  learner passage. That removes the main reason TF-IDF was rejected in
  `approach_decision_textrank_vs_tfidf.md`. It beats count only on Biology
  (p<0.001) and on the learner key (0.719 vs 0.642, p=0.005), and is ahead
  on Trigonometry but not significantly (p=0.21).
- Keyness against the rest of the book is strongest on CK-12 lists, but
  those lists are by design the words specific to each lesson, which is
  exactly what it measures, and MyVIRS usually won't have a book to compare
  against. On the learner key it is not significantly better than count.
- Caveats: exploratory; the learner key has one labeler; this changes what
  "relevance" means and pushes topic words above everyday words, which
  pulls against the VIRS "most frequent words first" idea. Worth a
  pre-registered test, not a pipeline change yet.

## Files

| File | What |
|---|---|
| `../priority_ranking.py` | the new options |
| `../tests/test_priority_ranking.py` | tests for them |
| `check_count_ranking.py` | the check above |
| `results/count_ranking/summary.json`, `per_item.json` | means, tests, top 10s |
| `explore_keyness.py`, `results/exploratory/keyness.json` | keyness exploration |
| `../baseline-comparison/learner-key/answer_key.json` | learner-focused key (13 Biology passages, one labeler; the team should review it) |

## Re-run

```bash
pip install spacy scipy numpy num2words wordfreq
python3 -m spacy download en_core_web_sm
python3 evaluation/check_count_ranking.py --learner-key baseline-comparison/learner-key/answer_key.json   # ~30 s
python3 evaluation/explore_keyness.py --learner-key baseline-comparison/learner-key/answer_key.json
```
