# MyVIRS Walking Skeleton — Team A

## What this is

Just a quick proof that the basic path works: you give it a passage of
text and get back each word tagged with how common it is. Relevance
scoring was added in Sprint 2, see the Sprint 2 update below.

## What's in this folder

- `walking_skeleton.py` — the Sprint 1 script, tags each word with its frequency category
- `word_categories.json` — the word-to-category lookup, parsed directly out
  of the previous team's own database seed file (`data.sql`), not invented
- `textrank.py` — the Sprint 2 script, ranks words by contextual relevance
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
- Only tested on short sample passages so far, not a full textbook.
- Doesn't account for word forms ("cells" vs "cell") yet, same open
  team decision as the Sprint 1 script.
