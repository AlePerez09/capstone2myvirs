# Keyness relevance: test plan (written before scoring)

**MyVIRS Team A** · Written November 3, 2026, before any of the settings
below were scored. Card: rethink relevance (Isa).

## Question

Does a relevance score add anything beyond counting? Specifically: does
blending in **keyness** (how much more the lesson uses a word than everyday
English does) rank the words worth teaching better than the in-lesson
count alone, with the same filters?

## The method (fixed before scoring)

For each word family the pipeline returns, among the words the ranking keeps:

- **English frequency of the family** = the sum of `wordfreq`
  `word_frequency(form, "en")` over the headword and all its forms. Summing
  the forms keeps a family like *divide / division / divides* from looking
  rarer than it is.
- **Unknown words get no keyness** (score 0). Families with English
  frequency 0 are almost all extraction glitches and photo credits
  ("infigure", "calleddna", "splettstoesser": 97 of 6,143 families in a
  coverage check of 15 Biology lessons, done without the answer key).
- Two candidate formulas:
  - `tf_rarity` = count in lesson x (-log10 English frequency)
  - `log_ratio` = log(count / words in lesson) - log(English frequency),
    i.e. how many times more often the lesson uses the word than English does
- The keyness score becomes a percentile within the lesson (0 to 1), the
  same way the count is, and replaces TextRank as the relevance part:
  priority = (1 - w) x count percentile + w x keyness percentile.

Candidate weights w: 0.25, 0.5, 0.75, 1.0. So 8 settings in all
(2 formulas x 4 weights). Nothing else is varied.

Both arms use the same filters: stop words and layout words removed (as
always), generic verbs dropped, number words dropped.

## How the setting is chosen

Score the 8 settings on **CK-12 Biology only** (84 lessons, Vocabulary
first words, as in `run_evaluation.py`) and keep the one with the highest
MAP. Ties: the smaller weight. No other setting is tried after this.

## Tests (run once, on the chosen setting)

**Primary:** CK-12 **Trigonometry** (22 lessons, held out). Chosen keyness
setting vs. **count only** (w = 0, same filters). Wilcoxon signed-rank,
two-sided, on per-lesson average precision. Relevance "adds something" only if
the keyness MAP is higher **and** p < 0.05.

**Secondary:** the learner-focused key (13 Biology passages), same
comparison. Also reported for reference: the official frequency-only
baseline, and 0.75 count + 0.25 TextRank (`RECOMMENDED`).

**Sensitivity:** the same comparison with number words kept (the current
default).

## Honest caveats, stated in advance

- Earlier today an exploratory script (`explore_keyness.py`) already
  scored a simpler version of `tf_rarity` (headword only, no unknown-word
  rule) at three weights on all three keys, including Trigonometry. So
  Trigonometry is not fully unseen. No unseen book was available: the
  CK-12 Drive folder isn't reachable from here and the web is blocked.
- Trigonometry has only 22 lessons, so the test has little power.
- CK-12 Vocabulary lists are words the book repeats on purpose, which
  favors counting. The learner key has one labeler.
- If keyness does not win on Trigonometry, the result is reported as is:
  no extra settings will be tried to make it win.
