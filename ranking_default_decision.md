# Proposal: make subject-aware ranking the default

**MyVIRS Team A** · Proposed by Isa, Sprint 5 (card #1269). Status:
**waiting for the team's decision** (see the bottom of this page).

## What we're deciding

Today `priority_ranking.py` and `contract.py` use the Sprint 4 setting by
default: 0.5 × VIRS band + 0.5 × TextRank relevance. Our own evaluation
showed that setting does **worse** than ranking by frequency alone
(Biology 0.143 vs 0.164, p < 0.001; see [evaluation/RESULTS.md](evaluation/RESULTS.md)).
So the ranking Team B receives today is the weakest one we have measured.

**Proposal:** make `--subject-aware` the default ranking.

## Why subject-aware

It is the only option that passed a test written down before scoring, on
textbooks never used to build it ([KEYNESS3_RESULTS.md](evaluation/KEYNESS3_RESULTS.md)).
MAP against the CK-12 vocabulary lists, number words kept:

| Fresh book | Frequency-only | Counting alone | **Subject-aware** |
|---|---|---|---|
| Earth Science MS (81 lessons, science) | 0.234 | 0.295 | **0.395** (better in 61 lessons, worse in 20, p < 0.001) |
| Adv. Probability & Statistics (51 lessons, math) | 0.189 | 0.201 | **0.298** (better in 40, worse in 9, p < 0.001) |

On the learner-focused key (13 Biology passages, one labeler, number words
dropped) it scores 0.755 vs 0.642 for counting alone.

In plain terms: the top of the list moves from very common words and
number words toward the words each lesson is actually about, which is
closer to Prof. Dwyer's idea of "relevant" (the words a learner needs first
to understand the lesson's main topics).

## What it costs

- **It changes what "frequency first" means.** The VIRS band is no longer
  part of the score; frequency means how often the word appears in this
  text. Band, K level and grade are still in every record for Team B.
- **Evidence limits.** Two fresh books, all CK-12, answer key = CK-12
  vocabulary lists. It was the third relevance idea tried; the first two
  failed on math books.
- **Extra dependency and data:** `wordfreq` and the 400 KB reference pile
  `data/reference_pile.json.gz`.
- **The Sprint 4 result must stay reproducible.** We would add a preset
  (e.g. `--sprint4`) for the old 0.5 / 0.5 setting so
  `evaluation_criterion.md` and `evaluation/RESULTS.md` still match.

## Question for Eric: number words

Number words (one, two, forty, hundred) count as vocabulary because Eric
asked for them (Alejandro also mentioned Prof. Dwyer asked). Subject-aware
**keeps** them by default. Dropping them raises the scores, mostly in math:

| | Numbers kept | Numbers dropped |
|---|---|---|
| Earth Science | 0.395 | 0.409 |
| Probability & Statistics | 0.298 | 0.377 |

Part of that gain is the answer key: CK-12 vocabulary lists never contain
number words, so any number word in the top 10 counts as a miss even if a
learner does need it. The options for Eric:

1. **Keep numbers** in the default ranking (proposed; matches his request).
2. **Drop numbers by default**, with `--keep-numbers` to bring them back.
3. **Keep numbers but cap them**, e.g. at most two number words in the top
   10. Not built or tested yet.

Whichever is chosen, `--drop-numbers` stays available.

## If the team says yes, the follow-up work

1. `priority_ranking.py`: make `SUBJECT_AWARE` the default in
   `rank_records()` / `rank_text()` and the command line; add the
   `--sprint4` preset for the old setting.
2. `contract.py`: pass the passage text into the ranking (subject-aware
   needs the text to tell math from science; today `contract.py` only
   passes the records).
3. Tests: update the ones in `tests/test_priority_ranking.py` that assume
   0.5 / 0.5 (`FREQUENCY_WEIGHT == 0.5`, the priority-formula and grade
   bonus tests) so they test the `--sprint4` preset, and add tests for the
   new default.
4. Regenerate `data/contract/ck12-biology.json` and
   `sample-photosynthesis.json` so Team B gets the new ranking, and tell
   Team B the top words will change (the format does not).
5. Update `walkthrough.md` and `limitations.md`, which show and describe
   the old ranking.

## Decision

*To fill in after the team meeting.*

- Date:
- Who was there:
- Default ranking chosen: subject-aware / keep the Sprint 4 setting / other:
- Number words (Eric): keep / drop by default / cap / other:
- Notes:
