"""
MyVIRS Team A: format the ranked word list for Team B.

pipeline.py returns one record per word family with everything Team A
needs for analysis (stop words, null scores, match_source, and so on).
Team B only needs the ranked vocabulary words to show a learner. This
module turns the pipeline's records into that smaller, stable format,
described in team_b_output_format.md.

What it does to the pipeline records:
- Drops words that were never TextRank candidates (stop words, numbers,
  textbook layout words). Their textrank_score is None.
- Keeps the top N words (10 by default, as the requirements specify),
  or every candidate when there are fewer than N.
- Adds an explicit rank, starting at 1.
- Renames fields to what the requirements doc uses (word,
  relevance_score) and leaves out internal fields.
- Reserves combined_score and frequency_band as null. They will be
  filled in by the combined ranking, so Team B's code does not have to
  change when that lands.

Empty or unusable input returns a valid response with an empty word
list and a message, never an exception (Requirements, section 3).

Usage:
    python3 team_b_format.py --text "Paste a passage here."
    python3 team_b_format.py --text-file data/biology.txt --top 25
    python3 team_b_format.py --from-json data/biology.json --out data/biology_team_b.json

From Python:
    from team_b_format import rank_passage_for_team_b
    result = rank_passage_for_team_b("Cells are the basic units of life.")
"""

import argparse
import json
import sys

SCHEMA_VERSION = "1.0"
DEFAULT_TOP_N = 10
RANKING_METHOD = "textrank"

EMPTY_INPUT_MESSAGE = "The passage was empty, so no words were ranked."
NO_CANDIDATES_MESSAGE = (
    "No vocabulary words were found. The passage may only contain stop "
    "words, numbers, or very short words."
)


def _word_of(record):
    """Pipeline records use 'headword' with families on, 'word' without."""
    return record.get("headword") or record.get("word")


def _forms_of(record, word):
    """Headword first, then the other forms alphabetically, so the order is
    the same every run (Functional Requirement 9)."""
    forms = record.get("forms") or [word]
    others = sorted(f for f in set(forms) if f != word)
    return [word] + others


def format_for_team_b(records, top_n=DEFAULT_TOP_N, source_type="passage"):
    """Turn pipeline.analyze_text() records into the Team B response.

    records      the list analyze_text() returns (families on or off)
    top_n        how many words to return; None or 0 returns every candidate
    source_type  "passage" or "textbook", passed through for Team B's display
    """
    if top_n is not None and top_n < 0:
        raise ValueError("top_n must be 0 or more")

    candidates = [r for r in records if r.get("textrank_score") is not None]
    # Same order the pipeline uses, made explicit so this function does not
    # depend on the records arriving pre-sorted. The word itself breaks any
    # remaining tie so the order never changes between runs.
    candidates.sort(
        key=lambda r: (-r["textrank_score"], -r["count"], _word_of(r))
    )
    selected = candidates[:top_n] if top_n else candidates

    words = []
    for rank, r in enumerate(selected, start=1):
        word = _word_of(r)
        words.append({
            "rank": rank,
            "word": word,
            "forms": _forms_of(r, word),
            "part_of_speech": r.get("pos"),
            "count": r["count"],
            "relevance_score": round(r["textrank_score"], 4),
            "relevance_percentile": r.get("relevance"),
            "frequency_band": None,
            "combined_score": None,
        })

    response = {
        "schema_version": SCHEMA_VERSION,
        "ranking_method": RANKING_METHOD,
        "source_type": source_type,
        "total_candidates": len(candidates),
        "returned": len(words),
        "words": words,
    }
    if not words:
        response["message"] = NO_CANDIDATES_MESSAGE
    return response


def empty_response(message=EMPTY_INPUT_MESSAGE, source_type="passage"):
    return {
        "schema_version": SCHEMA_VERSION,
        "ranking_method": RANKING_METHOD,
        "source_type": source_type,
        "total_candidates": 0,
        "returned": 0,
        "words": [],
        "message": message,
    }


def rank_passage_for_team_b(text, top_n=DEFAULT_TOP_N, source_type="passage",
                            families=True):
    """Text in, Team B response out. This is the function Team B calls."""
    if not isinstance(text, str) or not text.strip():
        return empty_response(source_type=source_type)

    from pipeline import analyze_text  # loads spaCy, so import only when needed

    family_list = None
    if families:
        from wordfamilies import find_family_list
        family_list = find_family_list(None)
    records = analyze_text(text, families=families, family_list=family_list)
    return format_for_team_b(records, top_n=top_n, source_type=source_type)


def main():
    parser = argparse.ArgumentParser(description="Ranked word list for Team B")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="rank this passage")
    src.add_argument("--text-file", help="rank the text in this .txt file")
    src.add_argument("--from-json",
                     help="reformat records already saved by pipeline.py --out")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N,
                        help="how many words to return (0 = all candidates)")
    parser.add_argument("--source-type", choices=["passage", "textbook"],
                        help="defaults to textbook for files, passage for --text")
    parser.add_argument("--out", help="save the response to this JSON file")
    args = parser.parse_args()

    source_type = args.source_type or ("passage" if args.text else "textbook")

    if args.from_json:
        with open(args.from_json, encoding="utf-8") as f:
            response = format_for_team_b(json.load(f), args.top, source_type)
    else:
        if args.text_file:
            with open(args.text_file, encoding="utf-8") as f:
                text = f.read()
        else:
            text = args.text
        response = rank_passage_for_team_b(text, args.top, source_type)

    output = json.dumps(response, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Saved {response['returned']} words to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
