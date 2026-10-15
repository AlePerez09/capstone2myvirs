# Where the Problem Statement Moved — Sprint 3

**MyVIRS Team A** · Milan Kolich, Alejandro Perez Domenech, Miguel Rodriguez, Isa Sharief, Fernando Thaureaux Ruiz

## The problem statement we started with

The existing MyVIRS site gives every word one fixed difficulty category
(K1 to K3, AWL, STEM, HIGH, MID, LOW), no matter how the word is used.
Team A's job was to add a contextual relevance signal, adapted from
Beatriz Cariello's TextRank method, and combine it with the frequency
bands, so a learner sees the words that matter for the text in front of
them. We expected the combined ranking to beat frequency alone.

Sprint 3 was the first time we ran the system end to end on a real
textbook. This document records what we assumed going in, what we
actually found, and what changed as a result.

## 1. The corpus is CK-12 textbooks, not the original study's books

**Assumed:** relevance would run on the same Florida and California
textbooks that produced Eric's frequency lists, once Eric got the PDFs.

**Found:** the Florida books were never available as text, and Eric
could not download the California ones. Beatriz needs text PDFs, not
scanned ones, for her method. Eric was considering a "plan B" using
other sources.

**What changed:** we found 16 CK-12 science and math textbooks as
searchable PDFs (6 science, 10 math, middle and high school). Ehsan
confirmed to Eric that the CK-12 books are the ones used in the study.
Relevance now runs on CK-12 only, which matches the California half of
the original corpus but not the Florida half.

## 2. Whole textbooks needed changes to Beatriz's code

**Assumed:** her TextRank code (Appendix B) could be run on a textbook
as written, after switching it from Portuguese to English.

**Found:** a full textbook is longer than spaCy will process in one go
(about 1 million characters), and her word graph is a full
vocabulary-by-vocabulary matrix, which needs several GB of memory for a
textbook's vocabulary.

**What changed:** `pipeline.py` processes text in chunks and stores the
word graph as a sparse matrix. The full CK-12 Biology book now runs in
about 10 seconds. The algorithm and its settings (nouns, adjectives and
verbs, window of 4, damping 0.85) are unchanged.

## 3. Relevance alone surfaces general textbook verbs

**Assumed:** TextRank would push subject words to the top on its own,
as it did for Beatriz's Portuguese STEM corpus.

**Found:** on CK-12 Biology, words like "called," "include," "show,"
"cause," and "use" rank near the top. They aren't biology terms, but
textbooks use them in almost every definition ("this process is called
photosynthesis"), so they connect to everything in the word graph.

**What changed:** blending relevance with Eric's frequency bands is now
a requirement, not just an improvement, since most of these words are
high-frequency words students already know. Adding the worst of them to
the textbook stopword list is a second option we can test.

## 4. Relevance alone did not beat frequency

**Assumed:** relevance would find the words that matter better than
frequency does.

**Found:** Isa compared TextRank against a frequency-only baseline on
CK-12 Biology, using CK-12's own lesson vocabulary lists as the answer
key (`baseline-comparison/RESULTS.md`). Ranking the same candidate words
by count beat TextRank: average precision 0.198 vs. 0.150 per lesson,
with frequency better in 78 of 85 lessons. Most of the improvement over
raw word counts came from filtering out stop words, not from the graph.
The likely reason is that Beatriz's graph is unweighted: two words that
appear together 500 times get the same single link as words that appear
together once.

**What changed:** our claim is narrower now. We can't say relevance
beats frequency; we can only test whether the *combined* score does,
once the combined ranking is built. Two caveats keep the result from
being the final word: CK-12's vocabulary lists are words the book
repeats on purpose, which favors frequency, and Eric's idea of relevance
(the "mom and cook" example) is about different words than a glossary.
Weighting the graph's links by how often words appear together is the
first fix to try.

## 5. Word forms had to be grouped into families

**Assumed:** spaCy's lemmatizer would be enough to treat "cells" and
"cell" as one word.

**Found:** Eric's lists count word families (walk, walks, walked,
walker, unwalked), and spaCy only removes simple endings. Worse, the
pipeline kept each word's lemma from its first appearance, which in a
textbook is usually a title or table of contents entry. spaCy tagged
those as proper nouns, so "cells" and "cell" stayed separate even
though both are the same word.

**What changed:** `wordfamilies.py` groups forms into families using a
family list file when we have one, then conservative suffix and prefix
rules, then the lemma. Each word now uses its most common lemma across
the book. On CK-12 Biology, 9,389 word forms became 6,582 families, and
"cell" (2,002 uses) moved to the top of the relevance ranking. We still
need the authors' word family lists from Ehsan to match their grouping
exactly.

## 6. The word lists are smaller and less settled than expected

**Assumed:** MyVIRS had a complete, agreed word list to build on.

**Found:** only about 2,300 words could be recovered from the old site's
database, which Eric said is about 1/20th of what the site needs. Eric's
own files hold 3,450 (HIGH), 5,005 (MID) and 8,080 (LOW) entries with
raw counts, while the published article's high-frequency list has 2,168
families. Subject is stored only as cell color in his K-12 files.

**What changed:** the combined ranking reads Eric's five files, not the
recovered database, and the loader reads subject from cell color. Which
version of the lists is official is still an open question for Eric.

## What stayed the same

- The goal: rank the words in a text so the ones worth teaching come first.
- The vertical split: Team A owns relevance and ranking, Team B owns the site.
- The method: TextRank as Beatriz built it, now adapted to English and
  whole textbooks.

## What this means for Sprint 4

1. Build the combined ranking and re-run Isa's comparison with it. That
   is the test of whether the project's main claim holds.
2. Try weighted graph links and an expanded textbook stopword list, and
   compare again.
3. Run the pipeline on the other 15 CK-12 books, not just Biology.
4. Get the official word list version and the word family lists from Eric.
