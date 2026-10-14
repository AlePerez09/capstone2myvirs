# First comparison: TextRank vs. frequency-only baseline

**Textbook:** CK-12 Biology (`data/biology.txt` from the team repo, commit `29b84f2`)
**Script:** `compare_baseline.py` (runs in about 30 seconds)
**Raw outputs:** `results/book_level.json`, `results/lesson_level.csv`, `results/lesson_level_summary.json`

## Bottom line

On CK-12 Biology, the frequency-only baseline finds the textbook's own key terms **better** than TextRank.
TextRank is clearly better than raw word counts, but nearly all of that gain comes from the candidate filter
(nouns/adjectives/verbs, no stop words), not from the graph. Once both use the same filter, ranking by count wins.

**Scope:** this compares the frequency-only baseline against TextRank alone. The comparison against the combined
score (TextRank blended with the frequency bands) will follow once the combined ranking is built.

## How it was scored

There's no hand-labelled answer key, so I used the one CK-12 already provides. Every lesson starts with a
**Vocabulary** list of its key terms, and the book ends with a **Glossary** (664 entries, which match the
lessons' Vocabulary lists one for one). A ranking scores well when it puts those terms near the top.
Both lists are stripped out of the text before ranking, so neither method sees the answer key.

Entries run straight into their definitions ("nitrogen cycle interconnected pathways..."), so only the first
word of each term is certain. The answer key is that first word ("nitrogen").

Rankings compared, all using the pipeline's own pre-processing:

| Ranking | What it is |
|---|---|
| Raw frequency | every word, ranked by count (the right-hand column `pipeline.py` prints) |
| **Frequency-only baseline** | the same candidate words TextRank uses, ranked by count |
| TextRank | `pipeline.textrank()` exactly as committed |
| TextRank (converged) | same, with the convergence fix from the approach-decision doc, section 6 |

## Results per lesson (85 lessons, each run as its own passage)

This is closest to how MyVIRS will be used: one passage in, top 10 words out.

| Ranking | Precision@10 | Recall@10 | Mean avg. precision |
|---|---|---|---|
| Raw frequency | 0.094 | 0.143 | 0.108 |
| **Frequency-only baseline** | **0.161** | **0.240** | **0.198** |
| TextRank | 0.129 | 0.189 | 0.150 |
| TextRank (converged) | 0.128 | 0.187 | 0.154 |

TextRank vs. baseline, lesson by lesson:
- Average precision: TextRank better in 6 lessons, worse in 78, tied in 1 (Wilcoxon p < 0.001)
- Precision@10: better in 7, worse in 27, tied in 51 (Wilcoxon p < 0.001)

## Results on the whole book (575 glossary terms that appear in the text)

| Ranking | P@10 | P@50 | P@100 | P@500 | R@1000 | Avg. precision |
|---|---|---|---|---|---|---|
| Raw frequency | 0.00 | 0.14 | 0.15 | 0.20 | 0.30 | 0.154 |
| **Frequency-only baseline** | **0.60** | **0.32** | **0.28** | **0.24** | **0.37** | **0.191** |
| TextRank | 0.60 | 0.28 | 0.20 | 0.20 | 0.28 | 0.144 |
| TextRank (converged) | 0.60 | 0.30 | 0.21 | 0.20 | 0.29 | 0.149 |

The two rankings overlap heavily: 8 of the top 10 and 79 of the top 100 words are the same.

Top 20 on the whole book (`*` = glossary term):
- **Frequency-only:** cells, cell\*, plants, water\*, body\*, system, species\*, called, life\*, human\*, food\*, like, organisms, image, energy, blood\*, evolution\*, different, plant\*, cycle
- **TextRank:** called, cells, water\*, body\*, species\*, cell\*, plants, include, food\*, life\*, organisms, different, human\*, form, system, blood\*, large\*, shown, use, living

## Why TextRank loses here

- The graph is **unweighted**: two words that appear together 500 times get the same single edge as words that
  appear together once. That throws away repetition, which is exactly what signals a lesson's key term.
- Generic textbook verbs ("called", "include", "shown", "use") sit next to everything, so they get many edges and
  rise to the top. The README already flagged this.
- The convergence fix barely moves the numbers, so it's worth doing for correctness but won't change the ranking.

## Caveats

- One textbook only. The Drive folder with the other CK-12 books wasn't reachable from here; the script will run on
  any of them once their text is extracted with `pipeline.py --save-text`.
- The answer key uses the first word of each term, so words like "dependent" (from "dependent variable") count as key
  terms while "variable" doesn't.
- Word forms aren't merged, so "cells" never counts as a hit for "cell". This affects every ranking equally.
- **The answer key favors frequency.** CK-12's Vocabulary lists are words the book repeats on purpose, so a
  frequency ranking has a built-in advantage here. That is a different idea of relevance from words that matter to a
  passage's meaning without being repeated, which is what TextRank is meant to catch. A test set labelled for that
  kind of relevance could give a different result.

## Possible next steps

- Weight edges by how often words co-occur, then re-run this comparison.
- Add "called", "include", "shown", "use" to the textbook stopwords, then re-run.
- Run the same script on the other CK-12 books.

## How to run

```bash
pip install spacy scipy numpy && python -m spacy download en_core_web_sm
python3 compare_baseline.py --repo path/to/capstone2myvirs \
    --text path/to/capstone2myvirs/data/biology.txt --out results/
```
