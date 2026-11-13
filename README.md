# MyVIRS — Team A

## What this is

Team A's half of MyVIRS: you give it a passage of text or a whole
textbook, and it tells you which words matter. Sprint 1 tagged each
word with how common it is, Sprint 2 added relevance scoring, and
Sprint 3 runs the full pipeline end to end on real CK-12 textbooks.

**Before relying on the results, read [limitations.md](limitations.md):**
what the system doesn't do, including that our Sprint 4 evaluation did
not show the combined ranking beating frequency alone.

**New here? [walkthrough.md](walkthrough.md)** follows one text through every
step, from PDF to Team B's JSON, with real commands and output.

## Setup (one step)

Needs Python 3.10 to 3.13 ([python.org](https://www.python.org/downloads/);
on Windows, tick "Add python.exe to PATH"). From the repo folder run:

| System | Command |
|---|---|
| Windows (Command Prompt or PowerShell) | `setup.bat` |
| Mac, Linux, or Git Bash | `./setup.sh` |

It creates a virtual environment in `.venv`, installs everything in
`requirements.txt` (spaCy's English model included), and runs the tests.
It should end with `172 passed`. Then activate the environment each time
you open a new terminal:

```bash
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # Mac / Linux
source .venv/Scripts/activate    # Git Bash
```

Already have an environment you want to use? `pip install -r requirements.txt`
does the same install in one command. The install commands in the sprint
sections below are older; `requirements.txt` replaces all of them.

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
- `priority_ranking.py` — combines frequency band and relevance into one ranking
- `ranking_default_decision.md` — proposal and team decision on the default ranking
- `contract.py` — formats the ranked list as JSON for Team B (contract v1)
- `word_lists.py` — loads the word lists (the full VIRS list, or Eric's five Excel files) into one lookup table
- `data/virs_words.csv` — the full VIRS word list from the old site (~30,000 words), shared by Team B
- `tests/test_word_lists.py` — tests for the word list loader, using mock files
- `tests/test_pipeline.py` — tests for the relevance pipeline (pre-processing, TextRank, word families, numbers, relevance options)
- `tests/test_priority_ranking.py` — tests for the combined ranking
- `tests/test_contract.py` — tests for the Team B format (`contract.py` and the schema)
- `schema/contract_v1.schema.json` — the contract format, for both teams to validate against
- `data/` — extracted textbook text and pipeline results (e.g. `biology.txt`, `biology.json`)
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

Install (see Setup at the top):

```bash
pip install -r requirements.txt
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

Install (see Setup at the top):

```bash
pip install -r requirements.txt
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

## Combined ranking and the Team B format

`priority_ranking.py` turns the pipeline's output into one ranked list,
following Isa's integration layer design (first version by Fernando):

```
priority = 0.5 × band score + 0.5 × relevance
```

- Band score: HIGH 1.0, MID 0.6, LOW 0.3, not in any list 0.1, plus 0.2
  (capped at 1.0) for K-12 list words at or below the text's grade.
- Relevance: the family's TextRank percentile in the text (0 to 1).
  Tied scores share a percentile.
- `--frequency-only` drops relevance, which is the baseline to compare against.
- Stop words and layout words ("figure," "page") are left out. Ties break
  by how often the word appears.

```bash
python3 priority_ranking.py --text-file data/biology.txt --top 25
python3 priority_ranking.py --text-file data/biology.txt --frequency-only
```

### Ranking options

Sprint 5 added these options to `priority_ranking.py`. **All are off by
default**, so the command above still gives the official Sprint 4 ranking
(0.5 × band + 0.5 × relevance). Each works on the command line and as an
argument to `rank_text()` / `rank_records()`.

Scores are MAP (mean average precision against the CK-12 vocabulary lists,
higher is better) next to the official **frequency-only** baseline on the
same lessons. "ns" means not statistically significant.

| Flag | What it does | Headline result | Full results |
|---|---|---|---|
| `--score-by count` | The frequency part becomes how often the word appears **in this text** (as a percentile), instead of its VIRS band. | With generic verbs dropped, counting alone beats frequency-only on Biology (0.219 vs 0.164) and the learner key (0.637 vs 0.538); ahead on Trigonometry but ns (0.222 vs 0.193). It also beat frequency-only on all three fresh books in the second relevance test. | [COUNT_RANKING_RESULTS.md](evaluation/COUNT_RANKING_RESULTS.md), [KEYNESS2_RESULTS.md](evaluation/KEYNESS2_RESULTS.md) |
| `--drop-generic-verbs` | Leaves out generic textbook verbs (include, use, find, produce, occur, ...). | Not tested alone. These verbs were one of the two reasons the combined ranking lost in Sprint 4, and the filter is part of every setting that beats frequency-only. | [COUNT_RANKING_RESULTS.md](evaluation/COUNT_RANKING_RESULTS.md), [RESULTS.md](evaluation/RESULTS.md) |
| `--drop-numbers` | Leaves out spelled-out number words (one, two, forty, ...). Off everywhere by default because numbers were requested as vocabulary. | Helps most on math text: with `--recommended`, Trigonometry goes from 0.220 (ns) to 0.277 vs 0.193 (p = 0.007); with `--subject-aware`, Probability & Statistics goes from 0.298 to 0.377 vs 0.189. CK-12 lists never contain number words, so this partly measures the answer key. | [COUNT_RANKING_RESULTS.md](evaluation/COUNT_RANKING_RESULTS.md), [KEYNESS3_RESULTS.md](evaluation/KEYNESS3_RESULTS.md) |
| `--recommended` | Shortcut for the Sprint 4 tuned setting: 0.75 × count + 0.25 × TextRank relevance, generic verbs dropped, numbers kept. | Biology 0.209 vs 0.164 (p < 0.001, tuned here), learner key 0.645 vs 0.538 (p = 0.01), Trigonometry 0.220 vs 0.193 (ns). TextRank itself adds nothing on CK-12 lists: counting alone does as well. | [COUNT_RANKING_RESULTS.md](evaluation/COUNT_RANKING_RESULTS.md) |
| `--relevance keyness` | Replaces TextRank with keyness: how much more this text uses a word than everyday English does. Needs `pip install wordfreq`. | **Did not pass** its pre-registered test. Strong on Biology (0.404, tuned there) and the learner key (0.721 vs 0.642 for counting, p = 0.03), but lower than counting on the held-out Trigonometry book (0.254 vs 0.293, ns). Tested with `--keyness-formula log_ratio --score-by count --frequency-weight 0.25 --relevance-weight 0.75 --drop-generic-verbs --drop-numbers`. | [KEYNESS_RESULTS.md](evaluation/KEYNESS_RESULTS.md), [KEYNESS_PROTOCOL.md](evaluation/KEYNESS_PROTOCOL.md) |
| `--subject-aware` | Decides from the text whether it is math or science, then uses the relevance that worked for that kind of text (0.25 × count + 0.75 × keyness against everyday English and/or a pile of other textbooks). Generic verbs dropped, numbers kept. | **Passed** its pre-registered test on two books never used before. Numbers kept (the default): Earth Science 0.395 vs 0.234, Probability & Statistics 0.298 vs 0.189, and better than counting alone on both (p < 0.001). With `--drop-numbers`, as originally tested: 0.409 and 0.377. | [KEYNESS3_RESULTS.md](evaluation/KEYNESS3_RESULTS.md), [KEYNESS3_PROTOCOL.md](evaluation/KEYNESS3_PROTOCOL.md) |

```bash
python3 priority_ranking.py --text-file data/biology.txt --subject-aware
python3 priority_ranking.py --text-file data/biology.txt --recommended --drop-numbers
```

Things to know before relying on these:

- Biology was used to pick the settings, so Biology numbers are in-sample.
  The fresh books (Earth Science, Probability & Statistics) and the learner
  key were not used for tuning.
- The learner key is 13 Biology passages labeled by one person; the team
  should review it (`baseline-comparison/learner-key/answer_key.json`).
- `--subject-aware` was the third relevance idea tried. The first two
  (`--relevance keyness`, and a version tested in
  [KEYNESS2_RESULTS.md](evaluation/KEYNESS2_RESULTS.md)) failed on math books.
- Which option becomes the default is a team decision, recorded in
  [ranking_default_decision.md](ranking_default_decision.md).

`contract.py` wraps that ranking in the contract v1 JSON from the design
doc and checks every response against `schema/contract_v1.schema.json`
before saving it. Team B can validate what they receive against the same
file.

```bash
python3 contract.py --text-file data/biology.txt --text-id ck12-biology \
    --corpus-id ck12-biology --out data/contract/ck12-biology.json
```

Sample outputs for Team B are in `data/contract/`: the whole Biology book
and a short photosynthesis passage.

Two changes from the design doc's proposal: `match_source` uses
`family_list`, `derived`, `lemma`, or `self`, and each word has an optional
`count` (times it appears in the text).

### Eric's word lists

`word_lists.py` reads Eric's five Excel files (HIGH, MID, LOW, and the two
K-12 grade lists) into one lookup table with each word's band, subject,
earliest grade, and frequency count. Subject comes from the cell color in
the K-12 files, and an unrecognized color stops with an error instead of
guessing.

```bash
pip install -r requirements.txt
python3 word_lists.py              # summary of what loaded
python3 word_lists.py --word cell  # look up one word
python3 tests/test_word_lists.py   # tests on mock files
```

Put the files in `data/word_lists/`. Once all five are there, the ranking
and `contract.py` use them automatically.

The loader was written from the layout Isa documented after reading the
files, and tested on mock files built the same way, because we didn't
have the files on hand this sprint. Running it on the real files is the
first thing to check; if their layout differs, adjust `COLUMN_NAMES`,
`COLOR_MAPS`, or `classify_color()`.

### The full VIRS word list

`data/virs_words.csv` is the complete word list from the old VIRS site,
recovered and shared by Team B: 44,034 rows covering 30,259 words, with
columns `value, category, grade`. Categories are K1, K2, K3 (school
frequency tiers), AWL and BAW (academic), STEM, and HI/MED/LOW (frequency
bands); about 6,000 words have a grade. It's the ~42,000-entry list the
old schema pointed to, and replaces the partial `word_categories.json`.

`word_lists.load_virs_csv()` turns it into the lexicon: HI/MED/LOW become
the band (K1-K3 words with no band count as HIGH), STEM and AWL/BAW become
the subject, and each word keeps its K level and earliest grade. The Team
B output now includes an optional `k_level` field, and `subject` can be
`stem`.

Which list is used, in order: Eric's five Excel files (if in
`data/word_lists/`), then `data/virs_words.csv`, then
`word_categories.json`.

Gaps: no number words (e.g. "hundred") and no multiword entries.

### Earlier note: the partial list

Without Eric's files, bands come from
`word_categories.json`, the ~2,300 words recovered from the old site.
That list isn't reliable as a frequency list: it labels "photosynthesis"
and "glucose" as K2 and "oxygen" as K1, but doesn't include "money." So
science words show up as HIGH. With the full list it's clear K1-K3 are
school-textbook tiers, so that's expected. The samples in `data/contract/`
now use the full VIRS list.

### Also fixed this sprint

- PDF ligatures: CK-12 PDFs store "fi" and "fl" as single characters
  ("ﬁsh," "ﬂowers"), about 2,500 times in Biology. The pipeline now
  normalizes them, so "ﬁsh" and "fish" count as one word.

### Numbers

At Eric's request, numbers count as vocabulary. Standalone digits are
spelled out first, the way Cariello's dissertation describes ("3,000" →
"three thousand," "2.5" → "two point five"), and number words like
"hundred" are counted, scored for relevance, and ranked even though spaCy
treats them as stop words.

Layout numbers are removed before that, so they don't flood the results:
section headings ("3.1 Cells"), table of contents page numbers, page
footers ("12 www.ck12.org"), and labels like "Figure 2.4" or "Lesson 5."
Numbers stuck to letters, like the 2 in CO2, are still dropped.

Requires `num2words` (`pip install num2words`). Use `--no-numbers` with
`pipeline.py` to drop numbers instead.

## Tests

The `tests/` folder checks the pipeline, the combined ranking, the Team B
format, and the word list loader. Run them all with one command from the
repo folder:

```bash
pip install -r requirements.txt
python -m pytest tests
```

It takes about 20 seconds. Each file also runs on its own, e.g.
`python tests/test_pipeline.py`.

| File | What it checks |
|---|---|
| `test_pipeline.py` | Ligatures, hyphenation, layout numbers, spelled-out numbers, chunking long text, TextRank, percentiles, word families, stop words, and the three relevance options |
| `test_priority_ranking.py` | Band scores, the grade bonus, the priority formula, tie-breaking, what's left out, and that the word list only has values the schema accepts |
| `test_contract.py` | Every response is valid, the code and schema agree on fields, the schema rejects broken responses, the samples in `data/contract/` stay valid, and the command line works |
| `test_word_lists.py` | Loading Eric's Excel files (mock files) and the VIRS CSV |

Some settings are pinned on purpose: Cariello's TextRank settings (window
of 4, damping 0.85, nouns/adjectives/verbs) and the weights and band
scores fixed in `evaluation_criterion.md`. If you change one deliberately,
update the test with it.

Tests marked **xfail** are known bugs, expected to fail until fixed:

- Other forms of textbook layout words ("explained," "sections,"
  "described") are still scored, because `TEXTBOOK_STOPWORDS` is checked
  against the exact word, not its lemma.
- A passage with only one candidate word gives it relevance 0, which the
  schema defines as "not a keyword."

When one is fixed, pytest reports `XPASS(strict)` and fails, as a
reminder to delete its `@pytest.mark.xfail` line.
