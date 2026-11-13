# System Walkthrough

**MyVIRS Team A** · Sprint 5 · November 2026

This follows one text through the whole system, from a PDF to the ranked
word list Team B receives, and shows what each step does and why. Every
command was run on the files in this repo and the output is copied as it
came out. For what the system doesn't do, see [limitations.md](limitations.md).

```
PDF ──► text ──► words + word families ──► relevance (TextRank)
                                                    │
     Team B JSON ◄── combined ranking ◄── frequency band (VIRS list)
```

| Step | File | What it does |
|---|---|---|
| 1. Read the PDF and clean the text | `pipeline.py` | pypdf text layer, ligatures, hyphenation, numbers |
| 2. Count words and group families | `pipeline.py`, `wordfamilies.py` | spaCy tokens, lemmas, suffix/prefix rules |
| 3. Score relevance | `pipeline.py` | TextRank, turned into a 0–1 percentile |
| 4. Rank for teaching | `priority_ranking.py`, `word_lists.py` | frequency band + relevance |
| 5. Hand off to Team B | `contract.py`, `schema/contract_v1.schema.json` | JSON checked against the schema |

## Setup

Run `setup.bat` (Windows) or `./setup.sh` (Mac, Linux, Git Bash) from the
repo folder, then activate `.venv` as the README's Setup section shows.
Or, in an environment you already have:

```bash
pip install -r requirements.txt
```

On Windows use `python` instead of `python3` in the commands below.

The example text is a short photosynthesis passage, saved in the repo as
both a PDF and plain text: `data/samples/photosynthesis.pdf` and
`data/samples/photosynthesis.txt`. Later we run the same steps on the whole
CK-12 Biology textbook.

## Step 1: Read the PDF and clean the text

```bash
python3 pipeline.py data/samples/photosynthesis.pdf --save-text photo.txt --top 10
```

`extract_pdf_text()` reads the PDF's text layer page by page with pypdf.
If a PDF has almost no text (a scanned book), it stops with an error that
says the file needs OCR, instead of returning an empty word list.

Before any word is counted, the text is cleaned:

| Function | Why |
|---|---|
| `normalize_text()` | Turns PDF ligatures back into letters (the single character "ﬁ" in "ﬁsh" becomes "fi"), using Unicode NFKC. Without it "fish" and "ﬁsh" are two different words. |
| `pre_process_hyphenation()` | Rejoins words broken across lines ("photo-\nsynthesis" → "photosynthesis"). |
| `strip_layout_numbers()` | Removes numbers that are layout, not vocabulary: section headings ("2.4 Cell Division"), page footers ("12 www.ck12.org"), and labels like "Figure 2.4." Otherwise they flood the list with "two" and "four." |
| `spell_out_numbers()` | Turns the remaining digits into words ("45" → "forty-five") with num2words, because the Product Owner wants number words taught. |

`--save-text` writes the cleaned extraction so you can see exactly what
the rest of the system read:

```
Photosynthesis is the process by which plants use the energy of sunlight to make food. It takes place in
the chloroplasts, small structures inside plant cells. Chloroplasts contain chlorophyll, a green pigment
that absorbs light energy. ...
```

## Step 2: Count words and group word families

spaCy (`en_core_web_sm`) splits the text into sentences and words and tags
each word's part of speech and lemma (dictionary form). Following
Cariello's Appendix A, `keep_token()` drops punctuation, digits, URLs,
hyphenated pieces, and words of two letters or fewer ("is," "a," "of"),
so this 108-word passage counts as 90 words.

Then `wordfamilies.group_by_family()` puts the forms of a word together so
"plant" and "plants" count as one entry. It tries three sources in order,
and records which one matched in `match_source`:

1. `family_list`: a published word family list, if one is in `data/`
2. `derived`: conservative suffix and prefix rules (*-ness, -ly, un-*)
3. `lemma`: spaCy's dictionary form

A word that matches nothing is its own family (`self`). The output from
step 1's command starts with:

```
Unique word families: 55   Total words: 90
Families with more than one form: 3   (no family list, rules + lemma)
```

The three families with more than one form here are
`plant ← plants, plant`, `use ← use, using`, and `take ← takes, take`.

The rules are cautious on purpose: wrongly merging two words is worse than
leaving them apart. On a test sentence, "cells" joins "cell," but
"division" stays apart from "divide" and "biology" from "biological."

## Step 3: Score relevance with TextRank

Relevance answers the question "how central is this word to this text?"
`textrank()` is the English version of Cariello's Appendix B:

- **Candidates** are nouns, adjectives, and verbs that aren't stop words
  (plus number words), sentence by sentence.
- **Links:** two candidates are linked when they are within 4 words of
  each other in a sentence.
- **Scoring:** like Google's PageRank, a word scores high when it links to
  many words that themselves score high (damping 0.85, at most 10 rounds).
  The graph is stored as a sparse matrix so a whole textbook fits in memory.

Raw TextRank scores depend on text length, so `relevance_percentiles()`
turns them into a 0–1 percentile within the text: 1.0 is the most central
word, and words with tied scores share a percentile. Function words that
TextRank never scored get 0.

The rest of step 1's output puts the two ideas side by side:

```
Top by relevance (score)        Top by frequency (count)
  1. plant (2.24)               the (7)
  2. energy (1.95)              plant (5)
  3. photosynthesis (1.61)      energy (4)
  4. dioxide (1.45)             photosynthesis (4)
  5. chloroplast (1.45)         eat (3)
  6. air (1.36)                 that (3)
  7. carbon (1.34)              and (3)
  8. water (1.14)               dioxide (2)
  9. small (1.12)               chloroplast (2)
 10. green (1.04)               air (2)
```

Counting alone puts "the," "that," and "and" in the top 10. TextRank only
scores content words, so the topic words come first. Each word becomes one
record (from `--out photo.json`):

```json
{
  "headword": "chloroplast",
  "forms": ["chloroplasts"],
  "match_source": "lemma",
  "pos": "NOUN",
  "is_stop": false,
  "count": 2,
  "textrank_score": 1.446274,
  "relevance": 0.8857
}
```

## Step 4: Rank the words for teaching

```bash
python3 priority_ranking.py --text-file data/samples/photosynthesis.txt --top 10
```

`priority_ranking.py` looks each family up in the VIRS word list
(`data/virs_words.csv`, 30,259 words, loaded by `word_lists.load_virs_csv()`)
to get its frequency band, then combines:

```
priority = 0.5 × band score + 0.5 × relevance
band score: HIGH 1.0, MID 0.6, LOW 0.3, not on the list 0.1
```

Common bands score higher, following Eric's approach of teaching the most
frequent words first. If a grade is given (`--grade G7`), words listed at
or below that grade get +0.2, capped at 1.0. Stop words and layout words
("figure," "page," "chapter") are dropped here, which is why 55 families
become 37. Ties break by count.

```
Ranked 37 word families (frequency + relevance)

rank  headword        band   relevance  priority   count
   1  plant           HIGH        1.00     1.000       5
   2  energy          HIGH        0.97     0.986       4
   3  photosynthesis  HIGH        0.94     0.971       4
   4  dioxide         HIGH        0.91     0.957       2
   5  chloroplast     HIGH        0.89     0.943       2
   6  carbon          HIGH        0.83     0.914       2
   7  water           HIGH        0.80     0.900       2
   8  small           HIGH        0.77     0.886       1
   9  green           HIGH        0.74     0.872       1
  10  pigment         HIGH        0.71     0.857       1
```

`--frequency-only` drops relevance and ranks by band alone. This is the
baseline our evaluation compares against:

```bash
python3 priority_ranking.py --text-file data/samples/photosynthesis.txt --top 10 --frequency-only
```

```
rank  headword        band   relevance  priority   count
   1  plant           HIGH           -     1.000       5
   2  energy          HIGH           -     1.000       4
   3  photosynthesis  HIGH           -     1.000       4
   4  eat             HIGH           -     1.000       3
   5  animal          HIGH           -     1.000       2
   ...
```

Every word here is HIGH, so frequency alone can only sort by count. That
is the band problem described in limitations.md: nearly half the VIRS
list is HIGH, so the band separates words poorly.

## Step 5: Hand the result to Team B

```bash
python3 contract.py --text-file data/samples/photosynthesis.txt \
    --text-id sample-photosynthesis --top 5 --out photo_contract.json
```

```
Saved 5 words to photo_contract.json (valid contract v1.0)
Tokens: 90   HIGH coverage: 97.8%   Any list: 97.8%
```

`contract.py` wraps the ranking in the version 1 format agreed with Team B
and checks it against `schema/contract_v1.schema.json` with jsonschema
before saving. A wrong field or type fails here with an error, not later
as a broken page on Team B's side. The start of the file:

```json
{
  "contract_version": "1.0",
  "text_id": "sample-photosynthesis",
  "corpus_id": null,
  "text_summary": {
    "tokens": 90,
    "coverage_high": 0.9778,
    "coverage_lsw": 0.9778
  },
  "words": [
    {
      "headword": "plant",
      "forms": ["plants", "plant"],
      "match_source": "lemma",
      "pos": "NOUN",
      "band": "HIGH",
      "frequency_count": null,
      "subject": "general",
      "grade_level": "G1",
      "k_level": "K1",
      "relevance": 1.0,
      "priority": 1.0,
      "rank": 1,
      "count": 5
    },
    ...
```

`coverage_high` is the share of the text's words in the HIGH band, and
`coverage_lsw` is the share on any VIRS list. A ready-made full textbook
example is in `data/contract/ck12-biology.json`.

## The same steps on a whole textbook

The commands are the same. Only the input changes:

```bash
python3 pipeline.py CK_12_Biology.pdf --out data/biology.json --save-text data/biology.txt
python3 contract.py --text-file data/biology.txt --text-id ck12-biology \
    --corpus-id ck12-biology --out data/contract/ck12-biology.json
```

Long texts are split into chunks of about 100,000 characters at paragraph
breaks, so spaCy can handle a book of more than a million characters. CK-12
Biology gives 179,777 counted words and 6,373 ranked families. The top 10:

| Rank | Word | Band | Relevance | Count |
|---|---|---|---|---|
| 1 | cell | HIGH | 1.000 | 2,004 |
| 2 | two | HIGH | 1.000 | 1,298 |
| 3 | one | HIGH | 1.000 | 932 |
| 4 | include | HIGH | 0.999 | 436 |
| 5 | plant | HIGH | 0.999 | 1,081 |
| 6 | water | HIGH | 0.999 | 684 |
| 7 | body | HIGH | 0.999 | 743 |
| 8 | species | HIGH | 0.998 | 664 |
| 9 | form | HIGH | 0.998 | 476 |
| 10 | human | HIGH | 0.998 | 634 |

This shows the weaknesses our evaluation found. Number words ("two,"
"one") and generic verbs ("include," "form") are HIGH and connect to
everything, so they rise to the top next to real biology words.

## Tests

```bash
python3 -m pytest tests -q
```

```
172 passed in 17.91s
```

| File | Tests | Covers |
|---|---|---|
| `tests/test_pipeline.py` | 71 | cleaning, ligatures, numbers, families, TextRank, percentiles, empty and non-English input |
| `tests/test_priority_ranking.py` | 35 | the formula, frequency-only, stop and layout word filtering |
| `tests/test_ranking_options.py` | 12 | in-lesson counting, generic verb and number filters, keyness, subject-aware |
| `tests/test_contract.py` | 49 | Team B output passes the schema; bad output is rejected |
| `tests/test_word_lists.py` | 5 | the VIRS CSV and Eric's Excel layout (mock files) |

The two known bugs from Sprint 4 (relevance 0 for a one-word passage, and
forms like "explained" slipping past the layout-word filter) were fixed in
Sprint 5, so their tests now pass instead of being marked as expected
failures.

## Evaluation

```bash
python3 evaluation/run_evaluation.py --out evaluation/results
```

This ranks each CK-12 lesson on its own and checks the ranking against
the lesson's Vocabulary list, which is removed from the text first so no
ranking sees the answer. It compares combined against frequency-only with
mean average precision and a Wilcoxon signed-rank test.

The result: the combined ranking did not beat frequency-only (Biology
0.143 vs. 0.164; Trigonometry 0.162 vs. 0.192). Details are in
`evaluation_report.md` and `evaluation/RESULTS.md`.

## Where to change things

| To change | Edit |
|---|---|
| The 50/50 weights or band scores | `FREQUENCY_WEIGHT`, `RELEVANCE_WEIGHT`, `BAND_SCORES` in `priority_ranking.py` |
| TextRank window, damping, parts of speech | `WINDOW_SIZE`, `DAMPING`, `CANDIDATE_POS` in `pipeline.py` |
| Turn number words off | `--no-numbers` on `pipeline.py` |
| Use a published word family list | put it at `data/word_families.txt` or `--families-file` |
| Use Eric's Excel word lists | put the five files in `data/word_lists/` (picked up automatically) |
| The output format for Team B | `schema/contract_v1.schema.json` and `WORD_FIELDS` in `contract.py` |
