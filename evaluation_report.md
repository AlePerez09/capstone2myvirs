# Sprint 4 Testing and Evaluation Report

**MyVIRS Team A** · Milan Kolich, Alejandro Perez Domenech, Miguel Rodriguez, Isa Sharief, Fernando Thaureaux Ruiz
Report by Alejandro, November 2, 2026. Full numbers and scripts: `evaluation/RESULTS.md` (Isa).

## Summary

We set out to show that combining contextual relevance with word
frequency picks the words worth teaching better than frequency alone. We
wrote the success criterion down on October 26, before measuring, and
tested it on two CK-12 textbooks.

**The criterion was not met.** The combined ranking lost to frequency-only
on both books, significantly on Biology. An exploratory test found a
setting that does beat frequency on both books, but its win comes from
counting words within the lesson, not from relevance.

## 1. The criterion, as stated in advance

From `evaluation_criterion.md` (written October 26, committed October 28,
before the evaluation ran on November 1):

- **Tested:** the combined ranking (0.5 × frequency band + 0.5 × relevance)
  against the frequency-only baseline. Relevance-only and Fernando's
  relevance improvements were run as extra comparisons.
- **Answer key:** each CK-12 lesson's Vocabulary list, with the Vocabulary
  and Glossary text removed before ranking so no ranking sees the answer.
  Eric's top-ten picks were the planned second key.
- **Metric:** mean average precision (MAP) across lessons, plus precision@10.
- **Success bar:** combined beats frequency-only on both books with a
  Wilcoxon signed-rank p < 0.05. One book = partly met, neither = not met.
- **Fixed in advance:** the 0.5 / 0.5 weights and the band scores (HIGH 1.0,
  MID 0.6, LOW 0.3, not listed 0.1). Any other setting is exploratory: tuned
  on Biology, checked on Trigonometry.

## 2. What was tested

**Automated tests.** `tests/test_word_lists.py` has 5 tests covering the
word list loaders and their use in the ranking: Eric's Excel layout (on
mock files), unknown cell colors raising an error, grade header parsing,
the ranking using the loaded bands, and the full VIRS word list. All 5
pass. Wider tests for the pipeline, word families, number handling and
the Team B format were planned this sprint but not written, and carry
over to Sprint 5.

**Evaluation.** `evaluation/run_evaluation.py` (Isa), built on the Sprint 3
baseline comparison. Every ranking uses the same pipeline output and the
same filtering, so only the scoring differs.

- **Books:** CK-12 Biology (84 lessons with usable keys) and CK-12
  Trigonometry (22 lessons).
- **Word list:** the full VIRS list, `data/virs_words.csv` (30,259 words),
  since Eric's Excel files weren't available.
- **Answer key B (Eric's picks):** not received, so not used.

Two fixes were needed to use Trigonometry: its extracted text had most
spaces missing, so it was re-split automatically (`repair_spacing.py`),
and its Vocabulary lists vary in layout, so the 23 lists were
transcribed by hand (`trigonometry_vocab_key.json`).

## 3. Results

| Book | MAP frequency-only | MAP combined | Combined better / worse (lessons) | Wilcoxon p | Beats baseline? |
|---|---|---|---|---|---|
| Biology | **0.164** | 0.143 | 31 / 53 | 0.000005 | No, significantly worse |
| Trigonometry | **0.192** | 0.162 | 7 / 15 | 0.09 | No, lower but not significant |

All rankings, MAP (Biology / Trigonometry):

| Ranking | Biology | Trigonometry |
|---|---|---|
| Frequency-only (baseline) | 0.164 | 0.192 |
| **Combined (tested)** | 0.143 | 0.162 |
| Relevance-only | 0.173 | 0.182 |
| Raw count in the lesson (reference) | **0.213** | **0.213** |
| Combined + Fernando's three options (exploratory) | 0.140 | 0.171 |

**Verdict: not met.** Combined did not beat frequency-only on either book.

## 4. Where the results disagreed with what we hoped

We expected relevance to lift the right words above common ones. Instead:

- **Combined pushed common words up.** The words it added to the top 10
  were mostly HIGH-band words that TextRank also scores highly because
  they connect to everything: *one, two, water, produce, include, form*
  in Biology, and *find, three, four, function, use* in Trigonometry.
  Example, lesson 13.1 Prokaryotes: frequency-only's top 10 had
  *bacteria* and *archaea*; combined dropped *archaea* and added
  *organism, one, live, cause, find*.
- **The band score is the weak part.** Relevance on its own was slightly
  ahead of frequency-only on Biology (0.173 vs. 0.164, not significant),
  but blending it with the band score made it worse, because the band
  boosts the same common words TextRank over-rates. Nearly half the VIRS
  list (14,174 words) is HIGH, so the band separates words poorly.
- **Number words hurt.** Spelled-out numbers, added at Eric's request,
  are HIGH and well connected, so they crowd the top, especially in
  Trigonometry. They aren't the only cause: an earlier run with numbers
  skipped still lost on both books.
- **Fernando's improvements helped a little, mostly on the math book**
  (Trigonometry 0.171 vs. 0.162, p = 0.04), but not enough to change the
  verdict. The verb filter alone did best on Trigonometry (0.177).

## 5. Exploratory: what would pass (after the official result)

Following the criterion's rule, 160 settings were tuned on Biology only,
then checked on Trigonometry as a held-out test. The best was
0.75 × how often the word appears in the lesson + 0.25 × relevance, with
number words and generic verbs dropped:

| | Biology (tuned on) | Trigonometry (held out) |
|---|---|---|
| Frequency-only | 0.164 | 0.192 |
| This setting | 0.221 | 0.279 |
| Better / worse lessons | 75 / 9 | 19 / 3 |
| Wilcoxon p | < 0.001 | 0.007 |

It passes the bar on both books, including the one it was never tuned
on. **But relevance isn't why:** the same setting with relevance removed
does even better (0.231 and 0.293). What helps is counting words within
the lesson instead of using the VIRS band, and filtering number words and
generic verbs. The official verdict stays **not met**.

## 6. Limitations

- **The answer key favors frequency.** CK-12 Vocabulary lists are words
  the book repeats on purpose, so counting does well by design. This was
  stated in the criterion in advance. Eric's picks, which would be a
  fairer test of relevance, didn't arrive.
- **First word only.** Multiword terms are keyed by their first word, which
  gives odd keys like *include* from "included angle." A check using every
  word of each Trigonometry term gave the same result.
- **Small math sample.** Trigonometry has 22 lessons, so it has little
  statistical power.
- **Repaired text.** The Trigonometry text was re-spaced automatically;
  about 0.25% of words are still broken formula pieces.
- **Word list source.** The VIRS list was saved by a Team B member from the
  capstone site before it was removed. We assume it matches Eric's lists
  but haven't checked it against his Excel files.
- **Two CK-12 books only,** so results may not carry over to other
  publishers or subjects.

## 7. What this means and next steps

1. **On CK-12's vocabulary lists, relevance doesn't add anything beyond
   counting.** That doesn't prove relevance is useless for teaching, since
   this key rewards repetition. The next test should use a learner-focused
   key, like Eric's top-ten picks.
2. **Ask Eric before changing defaults.** Two changes look worthwhile:
   extending the generic-verb filter, and making number words optional.
   Number words stay on for now because he asked for them.
3. **Rethink the frequency part.** Counting within the text beat the VIRS
   band on both books. Worth discussing with Eric whether the band should
   play a smaller role, or a different one, like a grade-level filter.
4. **Finish the automated tests** for the pipeline, word families, numbers
   and Team B format in Sprint 5.
