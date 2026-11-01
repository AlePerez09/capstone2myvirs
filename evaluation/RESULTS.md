# Sprint 4 Evaluation Results

**MyVIRS Team A** · Run November 1, 2026 on repo commit `287499b`, following
`evaluation_criterion.md` (written October 26, before this run).
Card: "Run the evaluation" (Isa).

## Verdict: criterion NOT MET

The combined ranking did not beat frequency-only on either book. On
Biology it was significantly **worse**. On Trigonometry it was also lower,
but the difference was not significant.

| Book | Lessons | MAP frequency-only | MAP combined | P@10 frequency-only | P@10 combined | Combined better / worse | Wilcoxon p (AP) | Beats baseline? |
|---|---|---|---|---|---|---|---|---|
| CK-12 Biology | 84 | **0.164** | 0.143 | **0.150** | 0.131 | 31 / 53 | 0.000005 | No (significantly worse) |
| CK-12 Trigonometry | 22 | **0.192** | 0.162 | **0.086** | 0.082 | 7 / 15 | 0.09 | No (lower, not significant) |

Wilcoxon signed-rank test, two-sided, on per-lesson average precision,
combined vs. frequency-only. For P@10 the Wilcoxon p is 0.008 on Biology
(combined worse) and 0.65 on Trigonometry.

## All rankings (MAP / P@10)

| Ranking | Biology | Trigonometry |
|---|---|---|
| Frequency-only (baseline, `--frequency-only`) | 0.164 / 0.150 | 0.192 / 0.086 |
| **Combined (tested, 0.5 band + 0.5 relevance)** | 0.143 / 0.131 | 0.162 / 0.082 |
| Relevance-only (TextRank percentile) | 0.173 / 0.145 | 0.182 / 0.082 |
| Raw count in the lesson (reference, Sprint 3 style) | **0.213 / 0.168** | **0.213 / 0.086** |
| *Exploratory:* combined + all three of Fernando's options | 0.140 / 0.133 | 0.171 / 0.082 |
| *Exploratory:* combined + weighted links only | 0.140 / 0.135 | 0.168 / 0.077 |
| *Exploratory:* combined + textbook-verb filter only | 0.143 / 0.131 | 0.177 / 0.091 |
| *Exploratory:* combined + abbreviation grouping only | 0.143 / 0.131 | 0.162 / 0.082 |

## Fernando's improvements (extra result)

Run as a separate, exploratory result as the criterion says.
Combined with all three options vs. plain combined:

- Biology: better in 50 lessons, worse in 34, MAP 0.140 vs 0.143, p = 0.04.
  More lessons improve, but the average does not go up.
- Trigonometry: better in 16, worse in 5, MAP 0.171 vs 0.162, p = 0.04.
- Against frequency-only it still loses on both books (Biology 29 better /
  54 worse, p < 0.001; Trigonometry 6 / 16, p = 0.20).
- Abbreviation grouping changes nothing on Biology (no sin/cos/tan) and
  nothing on average on Trigonometry. No single option clearly accounts for
  the gain (the verb filter alone does best on Trigonometry, 0.177).

So the improvements help the combined ranking a little, mostly on the math
book, but not enough to change the verdict.

## Where combined lost

**Biology:** combined was worse in 53 of 84 lessons. Biggest losses:
13.1 Prokaryotes (AP 0.08 vs 0.21), 4.1 Energy for Life (0.47 vs 0.65),
21.3 The Muscular System (0.41 vs 0.53), 14.2 Types of Protists (0.16 vs 0.27),
7.2 Protein Synthesis (0.49 vs 0.59), 3.1 Introduction to Cells (0.10 vs 0.19).
Full list in `results/summary.json` (`losses`) and per-lesson numbers in
`results/biology_first_words_lessons.csv`.

**Trigonometry:** combined was worse in 15 of 22 lessons. Biggest losses:
Exact Values of Special Inverse Circular Functions (0.02 vs 0.50; the key
is one word, "unit", which frequency-only ranks second), General Definitions
of Inverse Trig Functions (0.27 vs 0.53), The Law of Sines (0.01 vs 0.23),
The Law of Cosines (0.01 vs 0.09).

**Why it loses.** The words combined pushes into the top 10 (that
frequency-only did not have there) are mostly common, HIGH-band words that
TextRank also scores highly because they connect to everything:

- Biology: *one* (13 lessons), *two* (8), *water* (8), *produce* (6),
  *include* (6), *form* (5), *organism*, *cell*, *food*, *body*, *know*, *occur*.
- Trigonometry: *find* (4 lessons), *three* (4), *four* (3), *function*,
  *point*, *angle*, *use*, *eight*, *forty*.

Example, 13.1 Prokaryotes. Key words: antibiotic, archaea, bacteria,
cyanobacteria, endospore, extremophile, plasmid, vector.
Frequency-only top 10 has *bacteria* and *archaea*; combined drops *archaea*
and adds *organism, one, live, cause, find*.

Two concrete things this points to:

1. **Number words.** `pipeline.py` keeps spelled-out numbers as vocabulary
   (Eric's request). They are HIGH band and TextRank-central, so they crowd
   the top of the combined list, especially on the math book. An earlier
   trial run with digits skipped instead of spelled out (num2words not
   installed) still had combined behind frequency-only on both books, so
   numbers are not the only cause, but they make it worse.
2. **Generic verbs** (*include, produce, find, use, know, occur*). The
   textbook-verb filter removes some of these but not all (*produce*,
   *occur*, *represent* are not on its list).

Relevance on its own (0.173) is slightly ahead of frequency-only on Biology
(not significant, p = 0.55), but combining it with the band score drags it
down, because the band score boosts exactly the common words that TextRank
also over-rates.

## What was run

- **Script:** `evaluation/run_evaluation.py`, built on Isa's Sprint 3
  `baseline-comparison/compare_baseline.py` (same lesson split and metrics).
  Every ranking uses the same `pipeline.analyze_text()` records and the same
  `priority_ranking.rank_records()` filtering (stop words, layout words,
  number handling, word families), so only the score differs.
- **Word list:** the full VIRS list, `data/virs_words.csv` (30,259 words;
  HIGH 14,174, MID 9,545, LOW 6,475). Eric's five Excel files are not in
  `data/word_lists/`, so the loader fell back to this, as
  `priority_ranking.load_default_lexicon()` is written to do. This is the
  same data as Eric's lists in CSV form, not the temporary
  `word_categories.json`.
- **Fixed in advance and not changed:** weights 0.5 / 0.5, band scores HIGH 1.0,
  MID 0.6, LOW 0.3, none 0.1. No grade bonus (no text grade given).
- **Pipeline defaults:** numbers spelled out (needs `pip install num2words`),
  no relevance options, except in the exploratory rows.
- **Answer key A (CK-12 lesson Vocabulary):** first word of each term, mapped
  to its word family headword. Vocabulary and Glossary text removed before ranking.
  - Biology: 84 lessons with key words found in the text (85 Vocabulary lists).
  - Trigonometry: 22 lessons (23 Vocabulary lists; one list's first words
    never appear in its lesson).
- **Answer key B (Eric's picks):** not received, so not used.

## Trigonometry: two things done to make it usable

1. **Repaired spacing.** `data/trigonometry.txt` was extracted with most
   spaces missing ("willreviewsomeimportantaspectsoftriangles"): 6,016
   run-together tokens of 20+ letters, about half the book's letters.
   `evaluation/repair_spacing.py` re-splits them using English word
   frequencies (the `wordfreq` package), the same method as the wordninja
   library. It first rejoins words broken across lines ("func-/tion"),
   keeps rare real math words whole (cosecant, coterminal, quadrantal,
   cofunction), and separates words from glued one-letter variables
   ("functionc (x)" → "function c (x)"). Result in
   `evaluation/data/trigonometry_spaced.txt`: no 20+ letter runs left, and
   only about 240 of 98,600 words (0.25%) are not ordinary English or math
   words, mostly glued formula pieces like "cosc" or "xsi". It is a repair,
   not a clean extraction; re-extracting from the PDF would still be better.
2. **Hand-transcribed answer key.** The Trigonometry Vocabulary layout
   varies (term before the definition, after it, on its own line, with a
   colon or a dash), so the Sprint 3 parser can't read it. The 23 lists are
   transcribed in `evaluation/data/trigonometry_vocab_key.json`. In this
   book each Vocabulary list comes at the *end* of its lesson.

Sensitivity check: using every word of each Trigonometry term as the key
(so "angle of depression" gives *angle* and *depression*), the result is
the same: frequency-only 0.314, combined 0.271, 8 better / 15 worse, p = 0.29.

## Limitations

- CK-12 Vocabulary lists are words the book repeats on purpose, which
  favors frequency (stated in advance in the criterion).
- First word of multiword terms only. This gives some odd key words:
  "included angle" → *include*, "law of sines" → *law*, "unit circle" → *unit*.
- Trigonometry has only 22 lessons, so the test has little power there.
- The Trigonometry text was repaired automatically (see above).
- Two CK-12 books only.

## Files

| File | What |
|---|---|
| `run_evaluation.py` | the evaluation |
| `repair_spacing.py` | spacing repair for trigonometry.txt |
| `data/trigonometry_spaced.txt` | repaired Trigonometry text |
| `data/trigonometry_vocab_key.json` | Trigonometry answer key |
| `results/summary.json` | all means, tests, losses, verdict |
| `results/*_lessons.csv` | per-lesson AP, P@10, R@10 for every ranking |
| `results/*_top10.json` | each ranking's top 10 per lesson, with the key |
| `explore_tuning.py` | exploratory tuning (Biology tuned, Trigonometry held out) |
| `results/exploratory/tuning_report.json` | all 160 settings and the held-out test |

## How to re-run

```bash
pip install spacy scipy numpy num2words wordfreq
python3 -m spacy download en_core_web_sm
python3 evaluation/repair_spacing.py data/trigonometry.txt evaluation/data/trigonometry_spaced.txt
python3 evaluation/run_evaluation.py --out evaluation/results   # about 3 minutes
```

## Exploratory: can any setting reach the bar? (run after the official result)

The official verdict above stays **not met**. The criterion fixed the
weights and band scores in advance, and allows other settings only as
exploratory work: tune on Biology, then report Trigonometry as the
held-out test. `explore_tuning.py` does exactly that. It tried 160
settings on Biology only, none of which look at the answer key:

- frequency part: VIRS band (official), band with K1 > K2 > K3, band + grade
  bonus, or the word's **count within the lesson** (as a percentile)
- relevance weight: 0, 0.25, 0.5, 0.75, 1
- number words kept or dropped; generic verbs (pipeline's textbook verbs
  plus produce, occur, represent, need, help, cause, form, define,
  determine, contain, allow, become) kept or dropped
- plain pipeline or Fernando's three options

**Best combined setting on Biology:** 0.75 × count-in-lesson percentile +
0.25 × relevance, number words and generic verbs dropped, plain pipeline.

| | Biology (tuned on, in-sample) | Trigonometry (held out) |
|---|---|---|
| MAP official frequency-only | 0.164 | 0.192 |
| MAP this setting | 0.221 | 0.279 |
| Better / worse lessons | 75 / 9 | 19 / 3 |
| Wilcoxon p | < 0.001 | 0.007 |

So this setting **would pass the bar on both books**, including the book
it was never tuned on. But read it carefully, because the win does not
come from relevance:

1. **The same setting with relevance weight 0 does even better** on both
   books (Biology 0.231, Trigonometry 0.293). Adding relevance makes it
   slightly worse (Biology significantly, p < 0.001; Trigonometry not
   significantly, p = 0.49).
2. What helps is **(a) using how often the word appears in the lesson
   instead of its VIRS band**, and **(b) dropping number words and generic
   verbs**. Raw count alone already beat the band score in the official run.
3. If the baseline also drops number words and generic verbs, the
   band-based combined ranking still loses to it (Biology 0.153 vs 0.175,
   Trigonometry 0.212 vs 0.266).
4. Finer K1 > K2 > K3 band scores made combined worse (Biology 0.093,
   Trigonometry 0.142). The grade bonus (text grade 10 or 11) changed
   nothing on either book.

**What this means for the team:** on CK-12 Vocabulary lists, the VIRS
band score is the weak part of the ranking, and relevance doesn't add
anything beyond counting. Two pipeline changes are worth considering
whatever we decide about relevance: extend the generic-verb filter, and
make dropping spelled-out number words an **option** (off by default).
Number words stay in for now, because they were specifically requested and
may matter for teaching even though CK-12 Vocabulary lists leave them out;
the team will ask before changing the default. Nothing in `pipeline.py` was
changed for this evaluation. Keep in mind the
CK-12 key favors frequency by design (see Limitations); the Sprint 3
learner-focused key, where relevance did help, is a fairer test of what
relevance is for.

Full grid, with Trigonometry scores for every setting shown for reference
only (not used to choose): `results/exploratory/tuning_report.json`.
