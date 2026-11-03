# Relevance, second try: test plan (written before scoring)

**MyVIRS Team A** · Written November 3, 2026, before any setting below was
scored on any book. Follows `KEYNESS_RESULTS.md`, where keyness against
everyday English helped Biology but lost to counting on Trigonometry.

## Why a second try

Keyness against everyday English pushes down math vocabulary, because math
terms are mostly everyday words with a special meaning (*unit*, *right*,
*law*, *identity*). A fairer reference is **other school textbooks**: in a
pile of textbook pages, *unit circle* lessons use *unit* far more than a
typical page does, while *include* or *example* are everywhere.

## Fresh test books (never scored before)

From the public CK-12 PDF collection (github.com/smile-pi/ck12_textbooks),
chosen by whether their Vocabulary lists can be read, before scoring:

- **CK-12 Chemistry** (science). Vocabulary = bold term lines after
  "Vocabulary"; lesson text from the end of that list to "Further Reading"
  or "Review Questions".
- **CK-12 Basic Geometry Concepts** and **CK-12 Basic Algebra Concepts**
  (math). Vocabulary = bold words in the paragraph after "Vocabulary"; lesson
  text = "Guidance" heading up to "Vocabulary" (explanation and worked
  examples, not the definitions).

Answer key: first word of each bold term (as in Sprint 4), mapped to word
families the same way. Lessons with no key word in their text are skipped.
Text extracted with PyMuPDF; `evaluation/fresh_books.py` does all of this.

## Reference textbook pile (for the new keyness)

Fixed list, none of them a test book or on the same subject as one:
CK-12 Earth Science HS, Life Science MS, People's Physics Concepts,
Calculus, Basic Probability and Statistics Concepts, plus Biology and the
repaired Trigonometry text. Each book is cut into 1,500-word chunks. A word
family's document frequency = number of chunks containing any of its forms.
When ranking a lesson from Biology or Trigonometry, that book's own chunks
are left out of the pile (the fresh books are never in it).

## Candidate relevance scores (each as a percentile within the lesson)

1. `english`: the log_ratio keyness from the first try (unchanged).
2. `textbooks`: count in lesson x log((chunks + 1) / (df + 1)), i.e.
   TF-IDF against the textbook pile.
3. `both`: the average of the `english` and `textbooks` percentiles.

priority = (1 - w) x count percentile + w x relevance, with w in
{0.25, 0.5, 0.75, 1.0}. So 12 settings. Same filters everywhere: stop
words, layout words, generic verbs and number words dropped.

## Choosing (on books already seen)

Score the 12 settings on Biology (84 lessons) and Trigonometry (22
lessons). Keep the one with the highest **average of the two books' MAPs**,
so the math book counts as much as Biology. Ties: smaller w. Nothing else
is tried afterwards.

## Test (run once, chosen setting vs count only, same filters)

Wilcoxon signed-rank, two-sided, on per-lesson average precision.

**Relevance passes** only if both hold:
1. Pooled over all fresh lessons (Chemistry + Geometry + Algebra), MAP is
   higher than count only, p < 0.05.
2. Pooled over the two fresh math books, MAP is not lower than count only.

Per-book results and the official frequency-only baseline are reported too.

## Caveats stated in advance

- The fresh keys use the first-word shortcut, and CK-12 lists favor
  counting, as before.
- The concepts books are short lessons; some have only one or two key words.
- If it fails, the result is reported as is.
