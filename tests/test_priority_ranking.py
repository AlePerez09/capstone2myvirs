"""Tests for the Sprint 5 ranking options in priority_ranking.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import priority_ranking as pr  # noqa: E402


def rec(head, count, relevance=0.5):
    return {"headword": head, "forms": [head], "count": count, "relevance": relevance,
            "is_stop": False}


LEX = {"cell": {"band": "HIGH", "subject": "general", "grade_level": None, "frequency_count": None}}


def test_count_percentiles_share_ties():
    assert pr.count_percentiles([1, 5, 5, 9]) == [0.0, 0.5, 0.5, 1.0]
    assert pr.count_percentiles([3]) == [0.0]


def test_defaults_unchanged_band_score():
    ranked = pr.rank_records([rec("cell", 1, 0.0), rec("plasmid", 9, 0.0)], LEX)
    assert [r["headword"] for r in ranked] == ["cell", "plasmid"]  # HIGH band wins


def test_score_by_count_prefers_repeated_words():
    ranked = pr.rank_records([rec("cell", 1, 0.0), rec("plasmid", 9, 0.0)], LEX, score_by="count")
    assert [r["headword"] for r in ranked] == ["plasmid", "cell"]


def test_numbers_kept_by_default_and_droppable():
    records = [rec("two", 5), rec("cell", 2)]
    assert "two" in [r["headword"] for r in pr.rank_records(records, LEX)]
    assert "two" not in [r["headword"] for r in pr.rank_records(records, LEX, drop_numbers=True)]


def test_generic_verbs_droppable():
    records = [rec("produce", 5), rec("include", 5), rec("cell", 2)]
    heads = [r["headword"] for r in pr.rank_records(records, LEX, drop_generic_verbs=True)]
    assert heads == ["cell"]


def test_recommended_setting():
    assert pr.RECOMMENDED == {"score_by": "count", "frequency_weight": 0.75,
                              "relevance_weight": 0.25, "drop_generic_verbs": True}


def test_keyness_prefers_words_rare_in_english():
    # same count: the subject word beats the everyday word
    records = [rec("thing", 3, 0.0), rec("chloroplast", 3, 0.0)]
    ranked = pr.rank_records(records, LEX, score_by="count", frequency_weight=0.0,
                             relevance_weight=1.0, relevance="keyness")
    assert [r["headword"] for r in ranked] == ["chloroplast", "thing"]


def test_keyness_ignores_unknown_glitches():
    scores = pr.keyness_scores([rec("calleddnaxq", 5), rec("cell", 1), rec("thing", 1)])
    assert scores[0] == 0.0 and scores[1] > scores[2]


def test_keyness_formulas():
    records = [rec("cell", 2), rec("mitochondria", 2), rec("make", 2)]
    for formula in ("tf_rarity", "log_ratio"):
        s = pr.keyness_scores(records, formula)
        assert s[2] == min(s)  # 'make' is everyday English


def test_math_detector():
    assert pr.is_math("Solve 3x + 4 = 19, so x = 5 and 2x = 10.")
    assert not pr.is_math("Photosynthesis is the process plants use to make food from light.")


def test_subject_relevance_needs_text():
    import pytest
    with pytest.raises(ValueError):
        pr.rank_records([rec("cell", 2)], LEX, **pr.SUBJECT_AWARE)


def test_textbook_keyness_prefers_lesson_specific_words():
    pile = (100, {"unit": set(range(5)), "example": set(range(90))})
    s = pr.textbook_keyness([rec("unit", 3), rec("example", 3)], pile)
    assert s[0] > s[1]
