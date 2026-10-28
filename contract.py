"""
MyVIRS Team A, Sprint 3: format the ranked word list for Team B.

Produces the version 1 contract from Isa's integration layer design: one
JSON response per text, one entry per word family, ranked so rank 1 is the
word to teach first. The format is defined in schema/contract_v1.schema.json,
and every response is checked against it before it's returned or saved, so
a mismatch shows up as an error here instead of a broken page on Team B's
side.

Changes from the proposal in the design doc:
- match_source uses the values our pipeline produces: family_list,
  derived, lemma, self (the doc proposed aws_table, bnc_coca_family, lemma).
- Each word also has an optional "count": times the family appears in the
  text. Adding optional fields is allowed within version 1.

Run:
    python3 contract.py --text-file data/biology.txt --text-id ck12-biology \
        --corpus-id ck12-biology --out data/contract/ck12-biology.json
    python3 contract.py --text "Paste a passage here." --text-id sample-001
"""

import argparse
import json
import os
from pathlib import Path

CONTRACT_VERSION = "1.0"
SCHEMA_FILE = Path(__file__).parent / "schema" / "contract_v1.schema.json"
WORD_FIELDS = ["headword", "forms", "match_source", "pos", "band", "frequency_count",
               "subject", "grade_level", "k_level", "relevance", "priority", "rank", "count"]


def validate(response):
    """Raise jsonschema.ValidationError if the response breaks the contract."""
    import jsonschema

    with open(SCHEMA_FILE, encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(response, schema)


def build_response(text, text_id, corpus_id=None, lexicon=None,
                   frequency_only=False, text_grade=None, top=None):
    """Raw text in, a contract v1 response (a dict) out."""
    import pipeline
    from priority_ranking import load_default_lexicon, lookup, rank_records

    lexicon = lexicon if lexicon is not None else load_default_lexicon()
    records = pipeline.analyze_text(text)

    # Coverage is over every counted word, stop words included
    tokens = sum(r["count"] for r in records)
    high = sum(r["count"] for r in records if lookup(r, lexicon)["band"] == "HIGH")
    listed = sum(r["count"] for r in records
                 if lookup(r, lexicon)["band"] in ("HIGH", "MID", "LOW"))

    ranked = rank_records(records, lexicon, frequency_only, text_grade)
    if top:
        ranked = ranked[:top]

    response = {
        "contract_version": CONTRACT_VERSION,
        "text_id": text_id,
        "corpus_id": corpus_id,
        "text_summary": {
            "tokens": tokens,
            "coverage_high": round(high / tokens, 4) if tokens else 0.0,
            "coverage_lsw": round(listed / tokens, 4) if tokens else 0.0,
        },
        "words": [{k: r[k] for k in WORD_FIELDS} for r in ranked],
    }
    validate(response)
    return response


def main():
    parser = argparse.ArgumentParser(description="MyVIRS contract v1 output for Team B")
    parser.add_argument("--text", help="passage to analyze")
    parser.add_argument("--text-file", help="saved .txt file to analyze")
    parser.add_argument("--text-id", required=True, help="ID for this text, e.g. ck12-biology")
    parser.add_argument("--corpus-id", help="set when the text is a whole textbook or subject")
    parser.add_argument("--grade", help="text grade for the grade bonus, e.g. G7")
    parser.add_argument("--frequency-only", action="store_true")
    parser.add_argument("--top", type=int, help="keep only the top N words")
    parser.add_argument("--out", help="save the JSON here (prints it otherwise)")
    args = parser.parse_args()

    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.error("give --text or --text-file")

    response = build_response(text, args.text_id, args.corpus_id,
                              frequency_only=args.frequency_only,
                              text_grade=args.grade, top=args.top)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2)
        s = response["text_summary"]
        print(f"Saved {len(response['words'])} words to {args.out} (valid contract v{CONTRACT_VERSION})")
        print(f"Tokens: {s['tokens']:,}   HIGH coverage: {s['coverage_high']:.1%}   "
              f"Any list: {s['coverage_lsw']:.1%}")
    else:
        print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
