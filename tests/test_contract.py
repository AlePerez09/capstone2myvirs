"""
Tests for the Team B format: contract.py and schema/contract_v1.schema.json.

Checks that every response contract.py builds is valid, that the schema
rejects broken responses, that the code and schema agree on the fields,
and that the sample files Team B uses (data/contract/) stay valid.

Run from the repo folder:

    python -m pytest tests             # every test file
    python tests/test_contract.py      # just this file
"""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import contract  # noqa: E402

LEXICON = {
    "cell": {"band": "HIGH", "subject": "stem", "k_level": "K1",
             "grade_level": "G4", "frequency_count": None},
    "water": {"band": "MID", "subject": "general", "k_level": None,
              "grade_level": "K", "frequency_count": 12},
    "glucose": {"band": "LOW", "subject": "science", "k_level": None,
                "grade_level": "G9", "frequency_count": 3},
}
PASSAGE = ("Photosynthesis happens in the cell. The cell uses water and glucose. "
           "Glucose gives the cell energy.")
TOP_LEVEL_FIELDS = {"contract_version", "text_id", "corpus_id", "text_summary", "words"}


def build(text=PASSAGE, text_id="test-001", **kwargs):
    return contract.build_response(text, text_id, lexicon=LEXICON, **kwargs)


def load_schema():
    with open(contract.SCHEMA_FILE, encoding="utf-8") as f:
        return json.load(f)


_VALID = None


def valid_response():
    """A fresh copy of one valid response, built once (spaCy is slow)."""
    global _VALID
    if _VALID is None:
        _VALID = build()
    return copy.deepcopy(_VALID)


# ---------- The schema itself ----------

def test_schema_is_a_valid_json_schema():
    jsonschema.Draft202012Validator.check_schema(load_schema())


def test_code_and_schema_agree_on_version():
    assert load_schema()["properties"]["contract_version"]["const"] == contract.CONTRACT_VERSION


def test_code_and_schema_agree_on_word_fields():
    """A field added to one but not the other would break Team B's side."""
    word = load_schema()["$defs"]["word"]
    assert set(word["required"]) <= set(contract.WORD_FIELDS), "a required field is never sent"
    assert set(contract.WORD_FIELDS) <= set(word["properties"]), "a field is sent but not in the schema"


# ---------- Shape of a response ----------

def test_response_is_valid():
    contract.validate(valid_response())


def test_top_level_fields():
    response = valid_response()
    assert set(response) == TOP_LEVEL_FIELDS
    assert response["contract_version"] == "1.0"
    assert response["text_id"] == "test-001"
    assert response["corpus_id"] is None


def test_corpus_id_is_passed_through():
    assert build(corpus_id="ck12-biology")["corpus_id"] == "ck12-biology"


def test_every_word_has_the_same_fields():
    for word in valid_response()["words"]:
        assert set(word) == set(contract.WORD_FIELDS)


def test_ranks_count_up_from_one_and_priority_goes_down():
    words = valid_response()["words"]
    assert [w["rank"] for w in words] == list(range(1, len(words) + 1))
    priorities = [w["priority"] for w in words]
    assert priorities == sorted(priorities, reverse=True)


def test_words_carry_the_lexicon_values():
    words = {w["headword"]: w for w in valid_response()["words"]}
    assert (words["cell"]["band"], words["cell"]["subject"], words["cell"]["k_level"]) \
        == ("HIGH", "stem", "K1")
    assert words["glucose"]["frequency_count"] == 3
    assert words["photosynthesis"]["band"] == "NONE"


def test_no_stop_words_sent_to_team_b():
    heads = {w["headword"] for w in valid_response()["words"]}
    assert not {"the", "and", "in"} & heads


def test_response_survives_a_json_round_trip():
    response = valid_response()
    assert json.loads(json.dumps(response)) == response


def test_response_is_repeatable():
    assert build() == build()


# ---------- text_summary ----------

def test_text_summary_math():
    """7 counted words, stop words included: cell x2 is HIGH, water is MID,
    the rest (The x2, needs, grows) aren't in the lexicon."""
    summary = build("The cell needs water. The cell grows.")["text_summary"]
    assert summary["tokens"] == 7
    assert summary["coverage_high"] == round(2 / 7, 4)
    assert summary["coverage_lsw"] == round(3 / 7, 4)


def test_high_coverage_never_exceeds_any_list_coverage():
    summary = valid_response()["text_summary"]
    assert 0 <= summary["coverage_high"] <= summary["coverage_lsw"] <= 1


# ---------- Options ----------

def test_top_keeps_the_best_words():
    full = valid_response()["words"]
    top = build(top=2)["words"]
    assert top == full[:2]


def test_top_larger_than_the_list_returns_everything():
    assert len(build(top=10_000)["words"]) == len(valid_response()["words"])


def test_frequency_only_has_no_relevance():
    response = build(frequency_only=True)
    contract.validate(response)
    assert all(w["relevance"] is None for w in response["words"])


def test_text_grade_gives_the_grade_bonus():
    words = {w["headword"]: w for w in build(text_grade="G5")["words"]}
    plain = {w["headword"]: w for w in valid_response()["words"]}
    assert words["water"]["priority"] > plain["water"]["priority"]      # grade K
    assert words["glucose"]["priority"] == plain["glucose"]["priority"]  # grade G9


# ---------- Edge cases ----------

def test_empty_text_is_rejected_with_a_clear_error():
    import pipeline
    with pytest.raises(pipeline.InputError, match="empty"):
        build("")


def test_stop_words_only_gives_no_words():
    response = build("It is what it is, and so on.")
    assert response["words"] == []


def test_empty_text_id_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        build(text_id="")


# ---------- The schema rejects broken responses ----------

def _set_word(field, value):
    def change(response):
        response["words"][0][field] = value
    return change


def _delete(path):
    def change(response):
        target = response
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]
    return change


BROKEN = {
    "wrong contract version": lambda r: r.update(contract_version="2.0"),
    "missing words": _delete(["words"]),
    "missing text_summary": _delete(["text_summary"]),
    "missing headword": lambda r: r["words"][0].pop("headword"),
    "missing rank": lambda r: r["words"][0].pop("rank"),
    "empty text_id": lambda r: r.update(text_id=""),
    "coverage above 1": lambda r: r["text_summary"].update(coverage_high=1.2),
    "negative tokens": lambda r: r["text_summary"].update(tokens=-1),
    "rank 0": _set_word("rank", 0),
    "rank not a number": _set_word("rank", "1"),
    "unknown band": _set_word("band", "ULTRA"),
    "unknown subject": _set_word("subject", "art"),
    "unknown match_source": _set_word("match_source", "guess"),
    "k_level K4": _set_word("k_level", "K4"),
    "grade G13": _set_word("grade_level", "G13"),
    "grade without G": _set_word("grade_level", "7"),
    "relevance above 1": _set_word("relevance", 1.5),
    "negative priority": _set_word("priority", -0.1),
    "no forms": _set_word("forms", []),
    "count 0": _set_word("count", 0),
}


@pytest.mark.parametrize("change", BROKEN.values(), ids=BROKEN.keys())
def test_schema_rejects(change):
    response = valid_response()
    change(response)
    with pytest.raises(jsonschema.ValidationError):
        contract.validate(response)


def test_optional_fields_can_be_left_out():
    response = valid_response()
    for word in response["words"]:
        del word["count"], word["k_level"]
    contract.validate(response)


def test_new_optional_fields_are_allowed_in_v1():
    """The schema says new optional fields may be added within v1."""
    response = valid_response()
    response["words"][0]["translation"] = "célula"
    contract.validate(response)


# ---------- Sample files for Team B ----------

SAMPLES = sorted((REPO / "data" / "contract").glob("*.json"))


@pytest.mark.parametrize("path", SAMPLES, ids=[p.name for p in SAMPLES])
def test_sample_files_are_valid(path):
    with open(path, encoding="utf-8") as f:
        response = json.load(f)
    contract.validate(response)
    words = response["words"]
    assert [w["rank"] for w in words] == list(range(1, len(words) + 1))
    priorities = [w["priority"] for w in words]
    assert priorities == sorted(priorities, reverse=True)


def test_sample_files_exist():
    assert {p.name for p in SAMPLES} >= {"ck12-biology.json", "sample-photosynthesis.json"}


# ---------- Command line ----------

def run_cli(*args):
    return subprocess.run([sys.executable, "contract.py", *args], cwd=REPO,
                          capture_output=True, text=True, timeout=120)


def test_command_line_prints_a_valid_response():
    result = run_cli("--text", "The cell needs water.", "--text-id", "cli-test", "--top", "3")
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    contract.validate(response)
    assert response["text_id"] == "cli-test"
    assert len(response["words"]) <= 3


def test_command_line_saves_to_a_file():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "nested" / "out.json"
        result = run_cli("--text", "The cell needs water.", "--text-id", "cli-test",
                         "--out", str(out))
        assert result.returncode == 0, result.stderr
        assert "valid contract" in result.stdout
        contract.validate(json.loads(out.read_text(encoding="utf-8")))


def test_command_line_needs_text_and_text_id():
    assert run_cli("--text-id", "x").returncode == 2
    assert run_cli("--text", "The cell needs water.").returncode == 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
