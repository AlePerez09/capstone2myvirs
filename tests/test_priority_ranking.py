"""
Tests for priority_ranking.py: band scores, the grade bonus, lexicon
lookup, and the combined ranking (priority = 0.5 x band + 0.5 x relevance).

Most tests use small hand-made records and a hand-made lexicon, so they
don't change when the word lists change. One test checks the real word
list loads with values the Team B contract accepts.

Run from the repo folder:

    python -m pytest tests                    # every test file
    python tests/test_priority_ranking.py     # just this file
"""

import copy
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import priority_ranking as pr  # noqa: E402

LEXICON = {
    "cell": {"band": "HIGH", "subject": "stem", "k_level": "K1",
             "grade_level": "G4", "frequency_count": None},
    "glucose": {"band": "MID", "subject": "general", "k_level": None,
                "grade_level": "G6", "frequency_count": 40},
    "zygote": {"band": "LOW", "subject": "science", "k_level": None,
               "grade_level": None, "frequency_count": 2},
    "habitat": {"band": "MID", "subject": "general", "k_level": None,
                "grade_level": "G3", "frequency_count": None},
    "nucleus": {"band": "MID", "subject": "general", "k_level": None,
                "grade_level": "G9", "frequency_count": None},
}


def rec(head, relevance=0.5, count=1, is_stop=False, forms=None):
    """A record shaped like pipeline.analyze_text() output."""
    return {"headword": head, "forms": forms or [head], "match_source": "self",
            "pos": "NOUN", "is_stop": is_stop, "count": count,
            "textrank_score": 1.0, "relevance": relevance}


def ranked_heads(records, **kwargs):
    return [r["headword"] for r in pr.rank_records(records, LEXICON, **kwargs)]


# ---------- Settings fixed in evaluation_criterion.md ----------

def test_weights_and_band_scores_unchanged():
    """evaluation_criterion.md fixed these before the Sprint 4 evaluation.
    Changing them invalidates the reported results, so it should be a
    deliberate decision, not an accident."""
    assert pr.FREQUENCY_WEIGHT == 0.5
    assert pr.RELEVANCE_WEIGHT == 0.5
    assert pr.BAND_SCORES == {"HIGH": 1.0, "MID": 0.6, "LOW": 0.3, "NONE": 0.1}
    assert pr.GRADE_BONUS == 0.2


# ---------- band_score ----------

@pytest.mark.parametrize("band, expected", [
    ("HIGH", 1.0), ("MID", 0.6), ("LOW", 0.3), ("NONE", 0.1), ("SOMETHING_ELSE", 0.1)])
def test_band_score(band, expected):
    assert pr.band_score({"band": band}) == expected


def test_grade_bonus_at_or_below_text_grade():
    assert pr.band_score({"band": "MID", "grade_level": "G3"}, "G5") == pytest.approx(0.8)
    assert pr.band_score({"band": "MID", "grade_level": "G5"}, "G5") == pytest.approx(0.8)
    assert pr.band_score({"band": "LOW", "grade_level": "K"}, "G1") == pytest.approx(0.5)


def test_no_grade_bonus_above_text_grade():
    assert pr.band_score({"band": "MID", "grade_level": "G7"}, "G5") == 0.6


def test_grade_bonus_is_capped_at_one():
    assert pr.band_score({"band": "HIGH", "grade_level": "G3"}, "G5") == 1.0


def test_no_grade_bonus_without_a_valid_grade():
    assert pr.band_score({"band": "MID", "grade_level": "G3"}) == 0.6
    assert pr.band_score({"band": "MID", "grade_level": "G3"}, "G99") == 0.6
    assert pr.band_score({"band": "MID", "grade_level": None}, "G5") == 0.6
    assert pr.band_score({"band": "MID"}, "G5") == 0.6


# ---------- lookup ----------

def test_lookup_by_headword():
    assert pr.lookup(rec("cell"), LEXICON)["band"] == "HIGH"


def test_lookup_falls_back_to_forms():
    """The VIRS list stores some words as forms, not headwords."""
    record = rec("cellz", forms=["cellz", "cell"])
    assert pr.lookup(record, LEXICON)["band"] == "HIGH"


def test_lookup_unknown_word():
    entry = pr.lookup(rec("flibbet"), LEXICON)
    assert entry == {"band": "NONE", "subject": "general", "grade_level": None,
                     "k_level": None, "frequency_count": None}


# ---------- rank_records: the priority formula ----------

def test_priority_formula():
    ranked = {r["headword"]: r for r in pr.rank_records(
        [rec("cell", 0.6), rec("glucose", 1.0), rec("zygote", 0.2), rec("flibbet", 0.0)],
        LEXICON)}
    assert ranked["cell"]["priority"] == pytest.approx(0.5 * 1.0 + 0.5 * 0.6)
    assert ranked["glucose"]["priority"] == pytest.approx(0.5 * 0.6 + 0.5 * 1.0)
    assert ranked["zygote"]["priority"] == pytest.approx(0.5 * 0.3 + 0.5 * 0.2)
    assert ranked["flibbet"]["priority"] == pytest.approx(0.5 * 0.1)


def test_custom_weights():
    ranked = pr.rank_records([rec("glucose", 1.0)], LEXICON,
                             frequency_weight=1.0, relevance_weight=0.0)
    assert ranked[0]["priority"] == pytest.approx(0.6)


def test_missing_relevance_counts_as_zero():
    ranked = pr.rank_records([rec("cell", relevance=None)], LEXICON)
    assert ranked[0]["relevance"] == 0.0
    assert ranked[0]["priority"] == pytest.approx(0.5)


def test_grade_bonus_changes_the_order():
    """Both MID. nucleus is a G9 word and slightly more relevant, so it wins
    without a grade (0.60 vs 0.55). In a G5 text, habitat (a G3 word) gets the
    bonus and moves ahead (0.65 vs 0.60)."""
    records = [rec("nucleus", 0.6), rec("habitat", 0.5)]
    assert ranked_heads(records) == ["nucleus", "habitat"]
    assert ranked_heads(records, text_grade="G5") == ["habitat", "nucleus"]


def test_priority_always_between_zero_and_one():
    records = [rec(w, relevance) for w in LEXICON for relevance in (0.0, 1.0)]
    records += [rec("flibbet", 0.0), rec("blorp", 1.0)]
    for grade in (None, "K", "G12"):
        for r in pr.rank_records(records, LEXICON, text_grade=grade):
            assert 0.0 <= r["priority"] <= 1.0


# ---------- rank_records: frequency-only baseline ----------

def test_frequency_only_ignores_relevance():
    ranked = {r["headword"]: r for r in pr.rank_records(
        [rec("cell", 0.0), rec("glucose", 1.0)], LEXICON, frequency_only=True)}
    assert ranked["cell"]["relevance"] is None
    assert ranked["cell"]["priority"] == 1.0
    assert ranked["glucose"]["priority"] == 0.6
    assert ranked["cell"]["rank"] == 1


# ---------- rank_records: order and ranks ----------

def test_sorted_by_priority():
    priorities = [r["priority"] for r in pr.rank_records(
        [rec("zygote", 0.9), rec("cell", 0.1), rec("glucose", 0.5), rec("flibbet", 1.0)],
        LEXICON)]
    assert priorities == sorted(priorities, reverse=True)


def test_ties_break_by_count_then_alphabetically():
    records = [rec("bbb", 0.5, count=2), rec("aaa", 0.5, count=2), rec("ccc", 0.5, count=9)]
    assert ranked_heads(records) == ["ccc", "aaa", "bbb"]


def test_ranks_count_up_from_one():
    ranked = pr.rank_records([rec(w, 0.1 * i) for i, w in enumerate(LEXICON)], LEXICON)
    assert [r["rank"] for r in ranked] == list(range(1, len(LEXICON) + 1))


def test_no_records():
    assert pr.rank_records([], LEXICON) == []


# ---------- rank_records: what gets left out ----------

def test_stop_words_are_left_out():
    heads = ranked_heads([rec("cell"), rec("what", is_stop=True)])
    assert heads == ["cell"]


def test_spacy_stop_words_are_left_out_even_if_not_flagged():
    assert ranked_heads([rec("cell"), rec("the", is_stop=False)]) == ["cell"]


def test_layout_words_are_left_out():
    heads = ranked_heads([rec("cell")] + [rec(w) for w in pr.LAYOUT_WORDS])
    assert heads == ["cell"]


def test_number_words_are_kept():
    """Eric asked for numbers as vocabulary, even though spaCy calls them stop words."""
    heads = ranked_heads([rec("three", is_stop=True), rec("hundred", is_stop=True)])
    assert sorted(heads) == ["hundred", "three"]


# ---------- rank_records: output fields ----------

def test_output_adds_lexicon_fields_and_keeps_record_fields():
    original = rec("cell", 0.6, count=7, forms=["cell", "cells"])
    out = pr.rank_records([original], LEXICON)[0]
    for key, value in original.items():
        if key != "relevance":
            assert out[key] == value, key
    assert out["band"] == "HIGH"
    assert out["subject"] == "stem"
    assert out["grade_level"] == "G4"
    assert out["k_level"] == "K1"
    assert out["frequency_count"] is None
    assert out["rank"] == 1


def test_input_records_are_not_changed():
    records = [rec("cell", 0.6), rec("the", is_stop=True)]
    before = copy.deepcopy(records)
    pr.rank_records(records, LEXICON)
    assert records == before


# ---------- rank_text: end to end with the real pipeline ----------

PASSAGE = ("Photosynthesis happens in the cell. The cell uses water and glucose. "
           "Glucose gives the cell energy.")


def test_rank_text_end_to_end():
    ranked = pr.rank_text(PASSAGE, lexicon=LEXICON)
    by_head = {r["headword"]: r for r in ranked}
    assert by_head["cell"]["band"] == "HIGH"
    assert by_head["glucose"]["band"] == "MID"
    assert by_head["photosynthesis"]["band"] == "NONE"
    assert "the" not in by_head and "and" not in by_head
    assert [r["rank"] for r in ranked] == list(range(1, len(ranked) + 1))
    assert ranked[0]["headword"] == "cell"


def test_rank_text_frequency_only():
    ranked = pr.rank_text(PASSAGE, lexicon=LEXICON, frequency_only=True)
    assert all(r["relevance"] is None for r in ranked)
    assert ranked[0]["headword"] == "cell"


def test_rank_text_empty():
    assert pr.rank_text("", lexicon=LEXICON) == []


def test_rank_text_is_repeatable():
    assert pr.rank_text(PASSAGE, lexicon=LEXICON) == pr.rank_text(PASSAGE, lexicon=LEXICON)


# ---------- Lexicons ----------

def schema_enums():
    with open(REPO / "schema" / "contract_v1.schema.json", encoding="utf-8") as f:
        word = json.load(f)["$defs"]["word"]["properties"]
    return (set(word["band"]["enum"]), set(word["subject"]["enum"]),
            set(word["k_level"]["enum"]), re.compile(word["grade_level"]["pattern"]))


def test_default_lexicon_fits_the_contract():
    """Every value in the word list must be one the Team B schema accepts,
    or a word with that value would make contract.py fail."""
    bands, subjects, k_levels, grade_pattern = schema_enums()
    lexicon = pr.load_default_lexicon(verbose=False)
    assert len(lexicon) > 2000
    for word, entry in lexicon.items():
        assert entry["band"] in bands, (word, entry)
        assert entry["subject"] in subjects, (word, entry)
        assert entry.get("k_level") in k_levels, (word, entry)
        grade = entry["grade_level"]
        assert grade is None or grade_pattern.match(grade), (word, entry)
        count = entry["frequency_count"]
        assert count is None or isinstance(count, int), (word, entry)


def test_partial_word_list_mapping():
    lexicon = pr.lexicon_from_word_categories()
    bands, subjects, _, _ = schema_enums()
    assert all(e["band"] in bands and e["subject"] in subjects for e in lexicon.values())
    with open(pr.CATEGORY_FILE, encoding="utf-8") as f:
        categories = json.load(f)
    k1 = next(w for w, c in categories.items() if c == "K1")
    awl = next(w for w, c in categories.items() if c == "AWL")
    assert (lexicon[k1]["band"], lexicon[k1]["subject"]) == ("HIGH", "general")
    assert (lexicon[awl]["band"], lexicon[awl]["subject"]) == ("MID", "academic")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
