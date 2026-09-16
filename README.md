# MyVIRS Sprint 1 Walking Skeleton — Team A

## What this is

Just a quick proof that the basic path works: you give it a passage of
text and get back each word tagged with how common it is. It's not
supposed to be good yet, it's not supposed to know anything about
relevance either. That part's Sprint 2 and 3.

## What's in this folder

- `walking_skeleton.py` — the script itself
- `word_categories.json` — the word-to-category lookup, parsed directly out
  of the previous team's own database seed file (`data.sql`), not invented
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

## What's not here yet

- No relevance ranking (TextRank or anything else) yet, that's Sprint 2/3
- Doesn't talk to Team B's app, just runs on its own for now
- Doesn't handle word forms ("cells" vs "cell"), the old system didn't
  seem to either, so worth deciding as a team if we want to add that
