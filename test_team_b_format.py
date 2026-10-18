"""
Tests for team_b_format.py.

Run with:
    python3 -m unittest test_team_b_format -v

The first group uses hand-written records and needs no spaCy. The second
group runs real passages through the pipeline.
"""

import json
import unittest

from team_b_format import (
    DEFAULT_TOP_N,
    EMPTY_INPUT_MESSAGE,
    NO_CANDIDATES_MESSAGE,
    format_for_team_b,
    rank_passage_for_team_b,
)

WORD_FIELDS = [
    "rank", "word", "forms", "part_of_speech", "count",
    "relevance_score", "relevance_percentile", "frequency_band", "combined_score",
]


def record(head, score, count=1, forms=None, pos="NOUN"):
    return {
        "headword": head, "forms": forms or [head], "match_source": "self",
        "pos": pos, "is_stop": score is None, "count": count,
        "textrank_score": score, "relevance": 0.5 if score is not None else 0.0,
    }


class FormatterTests(unittest.TestCase):

    def test_drops_non_candidates(self):
        out = format_for_team_b([record("the", None, 50), record("cell", 2.0)])
        self.assertEqual([w["word"] for w in out["words"]], ["cell"])
        self.assertEqual(out["total_candidates"], 1)

    def test_ranks_by_score_and_numbers_from_one(self):
        recs = [record("b", 1.0), record("a", 3.0), record("c", 2.0)]
        out = format_for_team_b(recs)
        self.assertEqual([w["word"] for w in out["words"]], ["a", "c", "b"])
        self.assertEqual([w["rank"] for w in out["words"]], [1, 2, 3])

    def test_ties_broken_by_count_then_word(self):
        recs = [record("zeta", 1.0, 2), record("alpha", 1.0, 2), record("mid", 1.0, 9)]
        out = format_for_team_b(recs)
        self.assertEqual([w["word"] for w in out["words"]], ["mid", "alpha", "zeta"])

    def test_default_top_ten(self):
        out = format_for_team_b([record(f"w{i}", float(i)) for i in range(25)])
        self.assertEqual(out["returned"], DEFAULT_TOP_N)
        self.assertEqual(out["total_candidates"], 25)

    def test_fewer_than_ten_returns_all(self):
        out = format_for_team_b([record("a", 1.0), record("b", 2.0)])
        self.assertEqual(out["returned"], 2)

    def test_top_zero_returns_all(self):
        out = format_for_team_b([record(f"w{i}", float(i)) for i in range(25)], top_n=0)
        self.assertEqual(out["returned"], 25)

    def test_no_candidates_gives_message(self):
        out = format_for_team_b([record("the", None)])
        self.assertEqual(out["words"], [])
        self.assertEqual(out["message"], NO_CANDIDATES_MESSAGE)

    def test_every_word_has_the_same_fields(self):
        out = format_for_team_b([record("cell", 2.0, 5, ["cells", "cell"])])
        self.assertEqual(list(out["words"][0]), WORD_FIELDS)

    def test_headword_first_in_forms(self):
        out = format_for_team_b([record("cell", 2.0, 5, ["cells", "cell"])])
        self.assertEqual(out["words"][0]["forms"], ["cell", "cells"])

    def test_reserved_fields_are_null(self):
        w = format_for_team_b([record("cell", 2.0)])["words"][0]
        self.assertIsNone(w["frequency_band"])
        self.assertIsNone(w["combined_score"])

    def test_works_without_families(self):
        rec = {"word": "cells", "lemma": "cell", "pos": "NOUN", "is_stop": False,
               "count": 3, "textrank_score": 1.5, "relevance": 1.0}
        w = format_for_team_b([rec])["words"][0]
        self.assertEqual((w["word"], w["forms"]), ("cells", ["cells"]))

    def test_output_is_json_serializable(self):
        json.dumps(format_for_team_b([record("cell", 2.0)]))


class PipelineTests(unittest.TestCase):

    COOKING = ("My mom always makes dinner after work. She loves to cook pasta "
               "and bake bread on the weekend. Cooking is her favorite way to relax.")
    CELLS = ("Cells are the basic units of life. Every living organism is made of "
             "cells. The cell membrane controls what enters and leaves the cell.")

    def test_empty_and_whitespace_input(self):
        for text in ["", "   \n ", None]:
            out = rank_passage_for_team_b(text)
            self.assertEqual(out["words"], [])
            self.assertEqual(out["message"], EMPTY_INPUT_MESSAGE)

    def test_stop_words_only(self):
        out = rank_passage_for_team_b("It is what it is, and so on.")
        self.assertEqual(out["words"], [])
        self.assertIn("message", out)

    def test_real_passage(self):
        out = rank_passage_for_team_b(self.COOKING)
        self.assertGreater(out["returned"], 0)
        self.assertLessEqual(out["returned"], DEFAULT_TOP_N)
        scores = [w["relevance_score"] for w in out["words"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_families_merge_cell_and_cells(self):
        out = rank_passage_for_team_b(self.CELLS)
        top = out["words"][0]
        self.assertEqual(top["word"], "cell")
        self.assertEqual(top["forms"], ["cell", "cells"])

    def test_repeatable(self):
        self.assertEqual(rank_passage_for_team_b(self.CELLS),
                         rank_passage_for_team_b(self.CELLS))


if __name__ == "__main__":
    unittest.main()
