# Keyness relevance: results

**MyVIRS Team A** · Run November 3, 2026, following
`KEYNESS_PROTOCOL.md` (committed before scoring, `a188aed`).
Script: `evaluation/test_keyness.py`; numbers in `results/keyness_test.json`.

## Verdict: relevance is NOT shown to add anything in general

The keyness setting chosen on Biology did **worse** than counting alone on
the held-out Trigonometry book (not significantly). It did significantly
better on the learner-focused key, which is also Biology. So keyness helps
on Biology-style science text, but the planned test says it does not carry
over to the math book.

## Chosen on Biology

Of the 8 pre-set settings, the best on Biology was **log_ratio keyness,
weight 0.75**: priority = 0.25 x count percentile + 0.75 x keyness
percentile. (Biology MAP: tf_rarity 0.237 / 0.249 / 0.267 / 0.278 at
weights 0.25 / 0.5 / 0.75 / 1.0; log_ratio 0.335 / 0.379 / **0.404** / 0.289.)

## Tests (generic verbs and number words dropped in every row)

MAP, (lessons better / worse than count only), Wilcoxon two-sided p.

| | Biology (tuned on) | **Trigonometry (held out, primary)** | Learner key (secondary) |
|---|---|---|---|
| Frequency-only (official baseline) | 0.164 | 0.193 | 0.538 |
| Count only, no relevance | 0.231 | **0.293** | 0.642 |
| 0.75 count + 0.25 TextRank | 0.221 | 0.277 (p=0.49) | 0.654 (p=0.45) |
| **0.25 count + 0.75 keyness** | **0.404** (70/14, p<0.001) | 0.254 (7/15, p=0.26) | **0.721** (10/3, p=0.03) |

Sensitivity, number words kept: Trigonometry keyness 0.229 vs count 0.222
(9/13, p=0.66); learner key 0.724 vs 0.637 (p=0.03). Same picture.

Keyness still beats the official frequency-only baseline on all three keys.

## Why it loses on Trigonometry (looked at after the test; nothing re-tuned)

Keyness pushes words that are rare in everyday English to the top. In the
math book those are *cosine, tangent, sine, cotangent, radian, quadrant*;
in Biology they are exactly the key terms (*archaea, plasmid, endospore*).
But the Trigonometry Vocabulary lists are mostly everyday words with a
special math meaning: *unit* (circle), *right* (triangle), *law* (of sines),
*identity*, *domain*, *range*, *reference* (angle). Keyness pushes those down.

This is not just the "first word of each term" shortcut: with every word of
each term as the key, keyness loses more clearly (0.262 vs 0.424 for count
only, 4 better / 19 worse, p=0.002; post-hoc check).

So "rare in English" is a good sign of "this lesson is about it" for science
terms, and a bad one for math, where the important words are ordinary words
used in a new way. Whether *cosine* or *unit* should be taught first is a
question for the product owner; the CK-12 math key says *unit*.

## What this means

- Counting words in the lesson, with filler filtered out, is the robust
  improvement. It beats frequency-only on every key.
- Keyness is the first relevance score that clearly helps on Biology and on
  the learner key, where TextRank never did. It is not a general win.
- Options worth testing next, with a new plan written first: keyness only
  for science text; keyness against a subject word list instead of general
  English; or a learner key that also covers math.

## Caveats

- Trigonometry was partly seen earlier (a simpler keyness version was tried
  on it in `explore_keyness.py`). That earlier look favored keyness, so if
  anything it biased toward a keyness win, which didn't happen.
- 22 Trigonometry lessons; repaired text; one-labeler learner key on Biology.
