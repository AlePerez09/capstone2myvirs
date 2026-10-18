# MyVIRS — Team A

## What this is

Team A's half of MyVIRS: you give it a passage of text or a whole
textbook, and it tells you which words matter. Sprint 1 tagged each
word with how common it is, Sprint 2 added relevance scoring, and
Sprint 3 runs the full pipeline end to end on real CK-12 textbooks.

## What's in this folder

- `walking_skeleton.py` — the Sprint 1 script, tags each word with its frequency category
- `word_categories.json` — the word-to-category lookup, parsed directly out
  of the previous team's own database seed file (`data.sql`), not invented
- `textrank.py` — the Sprint 2 script, ranks words by contextual relevance
- `preprocessing.py` — Beatriz Cariello's pre-processing (Appendix A), adapted to English
- `approach_decision_textrank_vs_tfidf.md` — why we chose TextRank over TF-IDF
- `contextual_relevance_requirements.md` — requirements for the relevance model
- `pipeline.py` — the Sprint 3 end-to-end pipeline, textbook PDF in, ranked words out
- `wordfamilies.py` — groups word forms into word families (cells + cell → cell)
- `team_b_format.py` — formats the ranked word list in the format proposed for Team B
- `team_b_output_format.md` — the proposed Team B format, field by field
- `test_team_b_format.py` — tests for the Team B formatter
- `data/` — extracted textbook text and pipeline results (e.g. `biology.txt`, `biology.json`,
  and `biology_team_b.json`, a sample of the Team B format)
- `README.md` — this file

## How to run it

```bash
# Run on the built-in sample passage
python3 walking_skeleton.py

# Run on your own passage
python3 walking_skeleton.py "Paste any passage of text here."
```

## What it actually does

1. Takes a raw passage of text as input.
2. Splits it into words.
3. Looks up each word against the real category data inherited from the
   old MyVIRS system (K1, K2, Basic Academic Words, Academic Word List).
4. Prints each word tagged with its category, plus a summary count.

## Something worth flagging

We only got about 2,300 words out of the old database, way less than
the roughly 42,000 the schema's counter implied should be there. Even
running it on two short passages, common words like "is" and
"essential" came back unknown. Probably worth mentioning in our sprint
review, and worth asking Eric whether there's a fuller word list
somewhere we haven't found yet.

## The interface

The main function, `band_passage(text, categories)`, just takes a
string and hands back a list of word/category pairs in order. Kept it
this plain on purpose, so it's easy to plug into whatever we end up
agreeing on with Team B, without assuming anything about how they
display it.

## What's not here yet (Sprint 1)

- Doesn't talk to Team B's app, just runs on its own for now
- Doesn't handle word forms ("cells" vs "cell"), the old system didn't
  seem to either, so worth deciding as a team if we want to add that

## Sprint 2 update

`textrank.py` adds contextual relevance scoring, adapted from Beatriz
Cariello's TextRank implementation (originally built for Portuguese
STEM textbooks in her dissertation, ported here to English with
spaCy's `en_core_web_sm`).

Given a passage of text, it returns keywords ranked by how connected
they are to other important words in the passage, rather than by raw
frequency alone. This is the relevance signal that Isa's integration
layer design combines with the frequency bands from
`word_categories.json`.

### How to run it

Requires `spacy` and `numpy`:

```bash
pip install spacy numpy
python -m spacy download en_core_web_sm
```

Run on the built-in sample passage:

```bash
python3 textrank.py
```

Run on your own passage:

```bash
python3 textrank.py "Paste any passage of text here."
```

### What it actually does

1. Takes a raw passage of text as input.
2. Cleans and tokenizes it with spaCy, keeping nouns, adjectives, and
   verbs as candidates (same defaults as Cariello's original setup).
3. Builds a co-occurrence graph using a sliding window of 4 words.
4. Runs the TextRank (PageRank-style) algorithm to score each word's
   relevance.
5. Prints the top 10 keywords ranked by relevance score.

### What's not here yet (Sprint 2)

- Doesn't merge with `word_categories.json`'s frequency bands yet.
  That combination is Isa's integration layer, still in design.
- Only tested on short sample passages so far, not a full textbook
  (addressed in Sprint 3).
- Doesn't account for word forms ("cells" vs "cell") yet, same open
  team decision as the Sprint 1 script.

## Sprint 3 update

`pipeline.py` runs the whole relevance side end to end on a real
CK-12 textbook. It extracts the text from a searchable PDF, runs the
Appendix A pre-processing and the Appendix B TextRank in a single
spaCy pass, and returns one record per word with its part of speech,
lemma, count, and relevance score.

### How to run it

Requires `spacy`, `pypdf`, `scipy`, and `numpy`:

```bash
pip install spacy pypdf scipy numpy
python -m spacy download en_core_web_sm
```

Run on a textbook and save the results:

```bash
python3 pipeline.py CK_12_Biology.pdf --out data/biology.json --save-text data/biology.txt
```

Run on your own passage:

```bash
python3 pipeline.py --text "Paste any passage of text here."
```

Use `--top 30` to print more words.

### What changed from `textrank.py` to handle whole textbooks

- **PDF extraction:** reads the text layer of searchable PDFs with
  pypdf. Scanned PDFs are rejected with a clear error, since there's
  no OCR.
- **Chunking:** spaCy can only process about 1 million characters at
  once, and a textbook is longer than that, so the text is processed
  in pieces.
- **Sparse word graph:** the original code builds a full
  vocabulary-by-vocabulary matrix, which needs several GB of memory
  for a textbook's vocabulary. This version stores only the
  connections that exist.
- **Textbook stopwords:** layout and instruction words like "page,"
  "figure," "question," and "answer" are counted but never ranked as
  relevant, following Cariello's dissertation (section 3.5).

### First result: CK-12 Biology

The full textbook produced 9,389 words. Ranked by frequency, the top
words are "the," "and," "that," and "are." Ranked by relevance, they
are "called," "cells," "water," "body," "species," and "organisms."
The results are in `data/biology.json`, and the extracted text is in
`data/biology.txt` so teammates can test without the PDF.

### Word families

`wordfamilies.py` groups word forms into families before ranking, the
same unit Eric's lists use, so "cells" and "cell" become one entry with
a combined count and one node in the TextRank graph. Each word is
matched in this order, and the record says which step matched
(`match_source`):

1. `family_list`: a word family list file, if there is one in
   `data/word_families.txt` (or passed with `--families-file`). This
   should be the authors' own lists from Ehsan, or Nation's BNC/COCA
   families.
2. `derived`: conservative suffix and prefix rules (development →
   develop, activity → active, nonliving → live), used only when the
   base word also appears in the text.
3. `lemma`: spaCy's lemma (cells → cell, protected → protect).

Without a family list, "-er" nouns like "walker" aren't merged (the
rule would also turn "flower" into "flow"), and irregular forms like
"decision → decide" are missed.

Records now have `headword`, `forms`, and `match_source` instead of
`word`. To get the old one-entry-per-form output, add `--no-families`.

Re-run on the saved Biology text without the PDF:

```bash
python3 pipeline.py --text-file data/biology.txt --out data/biology.json
```

### What's not here yet (Sprint 3)

- No word family list file yet, so families come from rules and
  lemmas. Ask Eric for the authors' word family version of the lists.
- Some general academic words like "called," "include," and "shown"
  rank high because they connect to everything in a textbook. Blending
  in the frequency bands, or adding them to the textbook stopwords,
  should push them down.
- Not yet merged with Eric's frequency lists. That's the combined
  ranking card.

## Ranked word list for Team B

`team_b_format.py` turns the pipeline's records into the smaller format
Team B needs: only real candidates (no stop words or null scores), the
top 10 by default, an explicit rank, and every word with the same nine
fields. `frequency_band` and `combined_score` are reserved as `null` so
Team B's code won't need to change when the combined ranking lands. The
full format is in `team_b_output_format.md`, which is a proposal for
Team B to review.

```bash
# Rank a passage
python3 team_b_format.py --text "Paste any passage of text here."

# Reformat saved pipeline results (instant, no spaCy run)
python3 team_b_format.py --from-json data/biology.json --out data/biology_team_b.json

# Run the tests
python3 -m unittest test_team_b_format -v
```

From Python: `from team_b_format import rank_passage_for_team_b`.
