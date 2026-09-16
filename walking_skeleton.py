# MyVIRS Sprint 1 walking skeleton - Team A
#
# Takes a passage of text and tags each word with how common it is.
# Word list comes from the old team's database (K1, K2, BAW, AWL).
#
# Run it like this:
#   python3 walking_skeleton.py
#   python3 walking_skeleton.py "or put your own sentence here"

import json
import re
import sys
from pathlib import Path

CATEGORY_FILE = Path(__file__).parent / "word_categories.json"

CATEGORY_LABELS = {
    "K1": "K1 — most frequent 1000 words",
    "K2": "K2 — second most frequent 1000 words",
    "BAW": "Basic Academic Word",
    "AWL": "Academic Word List",
    "UNKNOWN": "Not yet categorized",
}


def load_word_categories(path: Path = CATEGORY_FILE) -> dict:
    # just reads the json file into a normal dict, nothing special
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tokenize(text: str) -> list:
    # breaks the passage up into words and drops the punctuation
    return re.findall(r"[A-Za-z']+", text)


def band_passage(text: str, categories: dict) -> list:
    # the actual core of the script: text goes in, and you get back
    # a list of words in order, each one tagged with its category.
    # kept it this simple so it's easy to slot into whatever Team B
    # ends up needing on their end
    words = tokenize(text)
    banded = []
    for word in words:
        category = categories.get(word.lower(), "UNKNOWN")
        banded.append({"word": word, "category": category})
    return banded


def summarize(banded: list) -> dict:
    # just tallies up how many words landed in each category
    counts = {}
    for item in banded:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    return counts


def print_report(text: str, banded: list) -> None:
    print("=" * 60)
    print("INPUT PASSAGE")
    print("=" * 60)
    print(text.strip())
    print()

    print("=" * 60)
    print("BANDED OUTPUT (word -> category)")
    print("=" * 60)
    for item in banded:
        label = CATEGORY_LABELS.get(item["category"], item["category"])
        print(f"  {item['word']:<15} -> {item['category']:<8} ({label})")
    print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    counts = summarize(banded)
    total = len(banded)
    for category, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = 100 * count / total if total else 0
        print(f"  {category:<8} {count:>4} words  ({pct:5.1f}%)")
    print(f"  {'TOTAL':<8} {total:>4} words")
    print()
    print("This is the frequency count for now. We'll add relevance in Sprint 2 and 3.")


SAMPLE_PASSAGE = (
    "The teacher asked the students to analyze the function of the "
    "ecosystem before the exam. Photosynthesis is the process by which "
    "plants convert light into energy, and it is a fundamental concept "
    "in biology."
)


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = SAMPLE_PASSAGE

    categories = load_word_categories()
    banded = band_passage(text, categories)
    print_report(text, banded)


if __name__ == "__main__":
    main()
