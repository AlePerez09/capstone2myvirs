"""
Tests for pipeline.py: pre-processing, chunking, TextRank, percentiles,
and analyze_text() end to end (word families, numbers, stop words, and
Fernando's three relevance options).

Run from the repo folder:

    python -m pytest tests            # every test file
    python tests/test_pipeline.py     # just this file

Tests marked xfail would be known bugs; none are open right now.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import pipeline  # noqa: E402

RECORD_FIELDS = {"headword", "forms", "match_source", "pos", "is_stop",
                 "count", "textrank_score", "relevance"}


def by_head(records):
    return {r["headword"]: r for r in records}


# ---------- Settings fixed by the requirements and evaluation criterion ----------

def test_cariello_settings_unchanged():
    """Requirements 4.3 and 4.6, and evaluation_criterion.md: nouns,
    adjectives and verbs, a window of 4, damping 0.85."""
    assert pipeline.CANDIDATE_POS == {"NOUN", "ADJ", "VERB"}
    assert pipeline.WINDOW_SIZE == 4
    assert pipeline.DAMPING == 0.85


# ---------- Pre-processing ----------

def test_ligatures_become_plain_letters():
    assert pipeline.normalize_text("ﬁsh and ﬂowers") == "fish and flowers"


def test_hyphenation_across_line_break_is_merged():
    assert pipeline.pre_process_hyphenation("photo-\nsynthesis") == "photosynthesis"
    assert pipeline.pre_process_hyphenation("photo-  \n  synthesis") == "photosynthesis"


def test_hyphen_inside_a_line_is_kept():
    assert pipeline.pre_process_hyphenation("a well-known cell") == "a well-known cell"


def test_layout_numbers_are_removed():
    text = ("3.1 Cells . . . . 53\n"
            "12 www.ck12.org\n"
            "See Figure 2.4 and Lesson 5 for 3,000 cells.\n"
            "www.ck12.org 7")
    lines = pipeline.strip_layout_numbers(text).split("\n")
    assert lines == ["Cells", "See Figure and Lesson for 3,000 cells."]


def test_numbers_are_spelled_out():
    pytest.importorskip("num2words")
    out = pipeline.spell_out_numbers("There are 3,000 cells, 45 plants and 2.5 liters.")
    assert "three thousand" in out
    assert "forty-five" in out
    assert "two point five" in out
    assert not any(ch.isdigit() for ch in out)


def test_numbers_stuck_to_letters_are_left_alone():
    pytest.importorskip("num2words")
    out = pipeline.spell_out_numbers("CO2 and x2 and H2O")
    assert out == "CO2 and x2 and H2O"


# ---------- Chunking ----------

def test_chunks_rejoin_to_original_text():
    text = "".join(f"Sentence number {i} is about cells.\n" for i in range(200))
    chunks = list(pipeline.chunk_text(text, size=300))
    assert len(chunks) > 1
    assert "".join(chunks) == text


def test_chunks_respect_size_and_cut_at_line_breaks():
    text = "".join(f"Sentence number {i} is about cells.\n" for i in range(200))
    chunks = list(pipeline.chunk_text(text, size=300))
    assert all(len(c) <= 300 for c in chunks)
    assert all(c.endswith("\n") for c in chunks[:-1]), "a word was cut in half"


def test_chunks_cut_at_sentence_end_without_line_breaks():
    text = "Cells divide. " * 100
    chunks = list(pipeline.chunk_text(text, size=100))
    assert "".join(chunks) == text
    assert all(c.endswith(".") for c in chunks[:-1])


def test_chunk_empty_text():
    assert list(pipeline.chunk_text("")) == []


# ---------- TextRank ----------

def test_textrank_no_words():
    assert pipeline.textrank([]) == {}
    assert pipeline.textrank([[], []]) == {}


def test_textrank_isolated_word_gets_base_score():
    scores = pipeline.textrank([["cell"]])
    assert scores["cell"] == pytest.approx(1 - pipeline.DAMPING)


def test_textrank_fully_connected_words_tie():
    scores = pipeline.textrank([["cell", "membrane", "energy"]])
    assert scores["cell"] == pytest.approx(scores["membrane"])
    assert scores["cell"] == pytest.approx(scores["energy"])


def test_textrank_window_size():
    """With a window of 2 only neighbors link, so a-b-c-d-e is a chain:
    the two ends tie and score lower than the middle."""
    scores = pipeline.textrank([["a", "b", "c", "d", "e"]], window_size=2)
    assert scores["a"] == pytest.approx(scores["e"])
    assert scores["a"] < scores["b"]


def test_textrank_links_stay_inside_a_sentence():
    scores = pipeline.textrank([["cell", "wall"], ["water", "energy"]])
    assert len(set(round(s, 9) for s in scores.values())) == 1


def test_unweighted_links_ignore_repetition():
    sentences = [["a", "b"]] * 5 + [["a", "c"]]
    scores = pipeline.textrank(sentences)
    assert scores["b"] == pytest.approx(scores["c"])


def test_weighted_links_reward_repetition():
    sentences = [["a", "b"]] * 5 + [["a", "c"]]
    scores = pipeline.textrank(sentences, weighted=True)
    assert scores["b"] > scores["c"]


# ---------- Relevance percentiles ----------

def test_percentiles_empty():
    assert pipeline.relevance_percentiles({}) == {}


def test_percentiles_run_from_zero_to_one():
    pct = pipeline.relevance_percentiles({"a": 0.2, "b": 0.5, "c": 0.9})
    assert pct == {"a": 0.0, "b": 0.5, "c": 1.0}


def test_tied_scores_share_a_percentile():
    pct = pipeline.relevance_percentiles({"a": 1.0, "b": 1.0, "c": 3.0})
    assert pct["a"] == pct["b"] == 0.25
    assert pct["c"] == 1.0


def test_single_candidate_is_not_reported_as_zero():
    assert pipeline.relevance_percentiles({"cell": 0.15})["cell"] > 0


# ---------- analyze_text: shape and ordering ----------

def test_empty_and_whitespace_text_are_rejected():
    for text in ("", "   \n\t "):
        with pytest.raises(pipeline.InputError, match="empty"):
            pipeline.analyze_text(text)


def test_record_fields():
    records = pipeline.analyze_text("Cells divide to make new cells.")
    assert records
    for r in records:
        assert set(r) == RECORD_FIELDS


def test_records_sorted_by_relevance_then_count():
    records = pipeline.analyze_text(
        "The cell membrane controls what enters the cell. Water moves across "
        "the membrane. Cells need water and energy to grow.")
    keys = [(r["relevance"], r["count"]) for r in records]
    assert keys == sorted(keys, reverse=True)


def test_relevance_between_zero_and_one():
    records = pipeline.analyze_text("Plants convert light into energy. Animals eat plants.")
    assert all(0.0 <= r["relevance"] <= 1.0 for r in records)


def test_unscored_words_have_zero_relevance():
    for r in pipeline.analyze_text("The cell is in the water."):
        if r["textrank_score"] is None:
            assert r["relevance"] == 0.0


def test_results_are_repeatable():
    """Requirements 4.9: same text and settings, same result."""
    text = "Cells are the basic units of life. Every organism is made of cells."
    assert pipeline.analyze_text(text) == pipeline.analyze_text(text)


# ---------- analyze_text: tokens and counting ----------

def test_short_words_digits_and_urls_are_not_counted():
    records = pipeline.analyze_text(
        "An ox ate 5 kg of CO2 at www.example.com today.", numbers=False)
    words = {f for r in records for f in r["forms"]}
    assert words == {"ate", "today"}


def test_counts_include_every_form():
    records = by_head(pipeline.analyze_text("Cells divide. A cell grows."))
    assert records["cell"]["count"] == 2
    assert sum(r["count"] for r in records.values()) == 4  # "A" is too short


def test_each_form_belongs_to_one_family():
    records = pipeline.analyze_text(
        "Cells grow. The cell grew. Growing cells develop. Development takes time.")
    heads = [r["headword"] for r in records]
    forms = [f for r in records for f in r["forms"]]
    assert len(heads) == len(set(heads))
    assert len(forms) == len(set(forms))


# ---------- analyze_text: word families ----------

def test_plural_joins_its_family():
    cell = by_head(pipeline.analyze_text("Cells divide. A cell grows."))["cell"]
    assert sorted(cell["forms"]) == ["cell", "cells"]
    assert cell["match_source"] in ("lemma", "self")


def test_without_families_each_form_is_separate():
    records = pipeline.analyze_text("Cells divide. A cell grows.", families=False)
    words = {r["word"]: r for r in records}
    assert "cells" in words and "cell" in words
    assert words["cells"]["lemma"] == "cell"
    assert "headword" not in words["cells"]


def test_derived_form_joins_base_word_in_text():
    develop = by_head(pipeline.analyze_text(
        "Plants develop slowly. Development takes time."))["develop"]
    assert sorted(develop["forms"]) == ["develop", "development"]
    assert develop["match_source"] == "derived"


def test_derived_form_stays_alone_without_base_word():
    records = by_head(pipeline.analyze_text("Development takes time."))
    assert "development" in records
    assert "develop" not in records


def test_ligature_and_plain_spelling_are_one_word():
    fish = by_head(pipeline.analyze_text("The ﬁsh swims. A fish eats."))["fish"]
    assert fish["count"] == 2


def test_word_split_across_lines_is_counted_whole():
    records = by_head(pipeline.analyze_text("Plants use photo-\nsynthesis for energy."))
    assert "photosynthesis" in records


# ---------- analyze_text: stop words and textbook words ----------

def test_stop_words_are_counted_but_not_scored():
    the = by_head(pipeline.analyze_text("The cell and the water."))["the"]
    assert the["is_stop"] is True
    assert the["count"] == 2
    assert the["textrank_score"] is None
    assert the["relevance"] == 0.0


def test_textbook_layout_words_are_not_scored():
    records = by_head(pipeline.analyze_text(
        "Students answer the questions in this chapter about cells."))
    for word in ("student", "answer", "question", "chapter"):
        assert records[word]["textrank_score"] is None, word
    assert records["cell"]["textrank_score"] is not None


def test_other_forms_of_textbook_layout_words_are_not_scored():
    records = by_head(pipeline.analyze_text(
        "Scientists explained how cells divide. The sections described cell growth."))
    for word in ("explain", "section", "describe"):
        assert records[word]["textrank_score"] is None, word


# ---------- analyze_text: numbers ----------

def test_numbers_are_vocabulary_by_default():
    pytest.importorskip("num2words")
    three = by_head(pipeline.analyze_text("There are 3 cells in the dish."))["three"]
    assert three["is_stop"] is False
    assert three["textrank_score"] is not None


def test_number_words_are_scored_even_though_spacy_calls_them_stop_words():
    three = by_head(pipeline.analyze_text("Three cells divide into six cells."))["three"]
    assert three["is_stop"] is False
    assert three["textrank_score"] is not None


def test_numbers_off_drops_digits():
    records = by_head(pipeline.analyze_text("There are 3 cells.", numbers=False))
    assert "three" not in records
    assert "cell" in records


def test_layout_numbers_do_not_become_words():
    pytest.importorskip("num2words")
    records = by_head(pipeline.analyze_text("See Figure 2.4 for the cell."))
    assert not {"two", "four", "point"} & set(records)


# ---------- analyze_text: Fernando's relevance options ----------

FILTER_TEXT = "Water is called a solvent. The cell includes a membrane."


def test_generic_verbs_are_scored_by_default():
    records = by_head(pipeline.analyze_text(FILTER_TEXT))
    assert records["call"]["textrank_score"] is not None
    assert records["include"]["textrank_score"] is not None


def test_filter_verbs_drops_generic_verbs_only():
    records = by_head(pipeline.analyze_text(FILTER_TEXT, filter_verbs=True))
    assert records["call"]["textrank_score"] is None
    assert records["include"]["textrank_score"] is None
    for word in ("water", "solvent", "cell", "membrane"):
        assert records[word]["textrank_score"] is not None, word


def test_filter_verbs_drops_heading_words():
    records = by_head(pipeline.analyze_text(
        "This introduction covers cell biology.", filter_verbs=True))
    assert records["introduction"]["textrank_score"] is None


def test_abbreviations_stay_separate_by_default():
    records = by_head(pipeline.analyze_text("We use sin to find the sine of angles."))
    assert "sin" in records and records["sine"]["count"] == 1


def test_group_abbreviations_counts_sin_as_sine():
    records = by_head(pipeline.analyze_text(
        "We use sin to find the sine of angles.", group_abbreviations=True))
    assert "sin" not in records
    assert records["sine"]["count"] == 2


def test_weighted_links_change_scores():
    text = "Cell membrane. Cell membrane. Cell membrane. Cell wall."
    plain = by_head(pipeline.analyze_text(text))
    weighted = by_head(pipeline.analyze_text(text, weighted=True))
    assert plain["membrane"]["textrank_score"] == plain["wall"]["textrank_score"]
    assert weighted["membrane"]["textrank_score"] > weighted["wall"]["textrank_score"]


# ---------- Long and real text ----------

def test_text_longer_than_one_chunk_is_fully_counted():
    """Over CHUNK_CHARS, so spaCy runs in several pieces; no word may be
    lost or split at a chunk boundary."""
    line = "The cell membrane protects the cell.\n"
    repeats = pipeline.CHUNK_CHARS // len(line) + 1500
    records = by_head(pipeline.analyze_text(line * repeats))
    assert len(line * repeats) > pipeline.CHUNK_CHARS
    assert records["cell"]["count"] == 2 * repeats
    assert records["membrane"]["count"] == repeats


def test_real_textbook_excerpt():
    """Runs on the start of CK-12 Biology and checks the output holds together."""
    path = REPO / "data" / "biology.txt"
    if not path.exists():
        pytest.skip("data/biology.txt not found")
    records = pipeline.analyze_text(path.read_text(encoding="utf-8")[:60_000])
    assert len(records) > 500
    heads = [r["headword"] for r in records]
    assert len(heads) == len(set(heads))
    assert all(0.0 <= r["relevance"] <= 1.0 for r in records)
    assert all(r["count"] >= 1 for r in records)
    assert not any(r["is_stop"] and r["textrank_score"] is not None for r in records)


def test_scanned_pdf_is_rejected():
    pypdf = pytest.importorskip("pypdf")
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "blank.pdf"
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(pdf, "wb") as f:
            writer.write(f)
        with pytest.raises(ValueError, match="OCR"):
            pipeline.extract_pdf_text(str(pdf))


# ---------- Bad input ----------

def test_input_error_is_a_value_error():
    assert issubclass(pipeline.InputError, ValueError)


def test_text_with_no_words_is_rejected():
    with pytest.raises(pipeline.InputError, match="no words"):
        pipeline.analyze_text("?? !! -- ## ab to")


@pytest.mark.parametrize("text", [
    "Las células se dividen para formar nuevas células y crecer en el cuerpo humano. "
    "El agua entra en la célula por la membrana, y la energía se produce en las "
    "mitocondrias de cada organismo vivo que existe en la Tierra.",
    "Les cellules se divisent pour former de nouvelles cellules dans le corps humain. "
    "L'eau entre dans la cellule par la membrane, et l'énergie est produite dans les "
    "mitochondries de chaque organisme vivant sur la Terre.",
    "Die Zellen teilen sich, um neue Zellen zu bilden und im Körper zu wachsen. "
    "Wasser gelangt durch die Membran in die Zelle, und die Energie wird in den "
    "Mitochondrien jedes lebenden Organismus auf der Erde erzeugt.",
    "细胞分裂形成新的细胞",
    "Клетки делятся, чтобы образовать новые клетки",
])
def test_non_english_text_is_rejected(text):
    with pytest.raises(pipeline.InputError, match="English"):
        pipeline.analyze_text(text)


def test_short_english_text_is_not_mistaken_for_another_language():
    assert pipeline.analyze_text("Development takes time.")


def test_missing_pdf_gives_clear_error():
    with pytest.raises(pipeline.InputError, match="File not found"):
        pipeline.extract_pdf_text("no/such/book.pdf")


def test_missing_text_file_gives_clear_error():
    with pytest.raises(pipeline.InputError, match="File not found"):
        pipeline.read_text_file("no/such/book.txt")


def test_pdf_with_no_pages_is_rejected(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    pdf = tmp_path / "empty.pdf"
    with open(pdf, "wb") as f:
        pypdf.PdfWriter().write(f)
    with pytest.raises(pipeline.InputError, match="no pages"):
        pipeline.extract_pdf_text(str(pdf))


def test_file_that_is_not_a_pdf_is_rejected(tmp_path):
    pytest.importorskip("pypdf")
    fake = tmp_path / "fake.pdf"
    fake.write_text("this is not a pdf")
    with pytest.raises(pipeline.InputError, match="PDF"):
        pipeline.extract_pdf_text(str(fake))


def test_binary_file_as_text_file_is_rejected(tmp_path):
    binary = tmp_path / "book.txt"
    binary.write_bytes(b"\xff\xfe\x00\x80\x81")
    with pytest.raises(pipeline.InputError, match="UTF-8"):
        pipeline.read_text_file(str(binary))


@pytest.mark.parametrize("args, message", [
    (["--text", ""], "empty"),
    (["--text", "细胞分裂形成新的细胞"], "English"),
    (["--text-file", "no/such/file.txt"], "File not found"),
    (["no/such/book.pdf"], "File not found"),
])
def test_command_line_bad_input_prints_message_not_traceback(args, message):
    result = subprocess.run([sys.executable, "pipeline.py", *args], cwd=REPO,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    assert result.stderr.startswith("Error:") and message in result.stderr
    assert "Traceback" not in result.stderr


# ---------- Command line ----------

def test_command_line_saves_records():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.json"
        result = subprocess.run(
            [sys.executable, "pipeline.py", "--text", "Cells divide. A cell grows.",
             "--out", str(out)],
            cwd=REPO, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        records = json.loads(out.read_text(encoding="utf-8"))
        assert "cell" in {r["headword"] for r in records}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
