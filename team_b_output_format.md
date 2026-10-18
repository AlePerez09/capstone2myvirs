# Ranked Word List Format for Team B

**Status:** Proposed by Team A, for Team B to review  
**Schema version:** 1.0  
**Code:** `team_b_format.py` · **Tests:** `test_team_b_format.py` · **Sample:** `data/biology_team_b.json`

## 1. Purpose

The requirements doc (section 3) left the exact format for passing ranked words to Team B to be "agreed upon during integration." This document is Team A's proposal. It is built from what `pipeline.py` produces today, trimmed to what Team B needs to show a learner, with room for the combined ranking that is still being built.

Please review the field list in section 3 and tell us what to rename, add, or drop. Changing it now costs little; changing it after both sides depend on it costs more.

## 2. How Team B gets the list

**From Python** (if Team B's backend runs Python):

```python
from team_b_format import rank_passage_for_team_b

result = rank_passage_for_team_b("Cells are the basic units of life. ...")
# result is a dict in the format below; json.dumps(result) gives the JSON
```

Optional arguments: `top_n=10` (use `0` for every candidate) and `source_type="passage"` or `"textbook"`.

**From the command line** (if Team B calls it as a separate process, or just wants files):

```bash
python3 team_b_format.py --text "Paste a passage here."
python3 team_b_format.py --text-file data/biology.txt --top 25 --out result.json
python3 team_b_format.py --from-json data/biology.json --out data/biology_team_b.json
```

`--from-json` reformats results already saved by `pipeline.py --out`, which is instant even for a full textbook.

If Team B needs an HTTP endpoint instead, the same function can sit behind one. That is a separate story once we know their stack.

## 3. The response

```json
{
  "schema_version": "1.0",
  "ranking_method": "textrank",
  "source_type": "textbook",
  "total_candidates": 4935,
  "returned": 10,
  "words": [
    {
      "rank": 1,
      "word": "cell",
      "forms": ["cell", "cells"],
      "part_of_speech": "NOUN",
      "count": 2002,
      "relevance_score": 23.9688,
      "relevance_percentile": 1.0,
      "frequency_band": null,
      "combined_score": null
    }
  ]
}
```

### Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Version of this format. Bumped if a field is renamed or removed, so Team B can detect breaking changes. |
| `ranking_method` | string | `"textrank"` today. Becomes `"combined"` once the combined ranking is in place. |
| `source_type` | string | `"passage"` or `"textbook"`. |
| `total_candidates` | integer | How many words were eligible for ranking (nouns, adjectives, and verbs that are not stop words). |
| `returned` | integer | How many words are in `words`. Equals `min(top_n, total_candidates)`. |
| `words` | array | The ranked words, most relevant first. Always present, possibly empty. |
| `message` | string | **Only present when `words` is empty.** A plain-English reason Team B can show the learner. |

### Fields on each word

| Field | Type | Meaning |
|---|---|---|
| `rank` | integer | Position in the list, starting at 1. |
| `word` | string | The word to show the learner. With word families on (the default) this is the family headword, e.g. `"cell"`. |
| `forms` | array of strings | Every form of the word that appeared in the text, headword first, then alphabetical. Useful for highlighting the word in the passage. |
| `part_of_speech` | string | spaCy tag: `NOUN`, `VERB`, or `ADJ`. |
| `count` | integer | Total times the word (all forms) appeared in the text. |
| `relevance_score` | number | Raw TextRank score, rounded to 4 decimals. Only comparable **within one response**: scores from a short passage and a whole textbook are on different scales. |
| `relevance_percentile` | number | 0 to 1, where 1 is the most relevant candidate in this text. Safer than `relevance_score` for display or thresholds. |
| `frequency_band` | string or null | **Reserved, always `null` for now.** Will hold the K1 / K2 / BAW / AWL / UNKNOWN band once the combined ranking is built. |
| `combined_score` | number or null | **Reserved, always `null` for now.** Will hold the blended relevance + frequency score. When it is filled in, `words` will be ordered by it. |

Every word always has all nine fields, in this order, so Team B never has to check whether a key exists.

## 4. Behavior Team B can rely on

- **Default length is 10.** If there are fewer than 10 eligible words, all of them are returned (Requirements, section 3).
- **Empty or unusable input never raises an error.** It returns `words: []` with a `message`:
  - Empty or whitespace-only text: `"The passage was empty, so no words were ranked."`
  - Text with no eligible words (only stop words, numbers, or very short words): a message saying no vocabulary words were found.
- **Results are repeatable.** The same text and settings always give the same response. Ties in `relevance_score` are broken by `count` (higher first), then alphabetically by `word`.
- **Stop words and textbook layout words are never returned** ("the," "figure," "chapter," and so on).
- **Translation is not included.** `word` is always English; translating it is outside Team A's component.

## 5. What the pipeline output has that this format leaves out

| Pipeline field | Why it is left out |
|---|---|
| Records with `textrank_score: null` | Stop words and non-candidates. About a quarter of the Biology records (1,647 of 6,582). |
| `match_source` | How the word family was matched. Useful to Team A for debugging, not to a learner. |
| `is_stop` | Always `false` for the words that remain. |
| `headword` / `word` | Unified into one field, `word`, so Team B handles one name whether word families are on or off. |

## 6. Known limitations

- **Generic textbook verbs rank high.** On CK-12 Biology, "call" (from "called") and "include" are ranks 2 and 3. Isa's baseline comparison and `problem_statement_changes.md` explain why. The combined ranking is expected to push them down; until then Team B should expect them.
- **Small scores tie on short passages.** In the cooking sample, "bake" and "pasta" share a score of 1.19. The tie-break keeps the order stable, but `relevance_percentile` still differs between them because it reflects list position.
- **No word family list yet.** Families come from rules and spaCy lemmas, so some forms may not merge (see `wordfamilies.py`).

## 7. Questions for Team B

1. Does your backend run Python, or do you need a file, a command-line call, or an HTTP endpoint?
2. Is 10 words the right default for the learner view, or do you want more?
3. Do you want `forms` for highlighting words in the passage, or should we drop it?
4. Any field names that clash with what your site already uses?
