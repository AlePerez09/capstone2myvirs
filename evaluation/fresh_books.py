"""
Read fresh CK-12 books (PDFs from github.com/smile-pi/ck12_textbooks) into
lessons with answer keys, and build the reference textbook pile, as
described in KEYNESS2_PROTOCOL.md.

Answer key = first word of each bold term in a lesson's Vocabulary section.

    python3 evaluation/fresh_books.py --pdfs path/to/ck12_textbooks/books --out evaluation/data/fresh
"""

import argparse
import json
import re
from pathlib import Path

HEADING_FONT = "NimbusSanL-Bold"
BOLD = 16  # PyMuPDF span flag
SKIP_FIRST = {"non", "one", "the", "a", "an"}

TEST_BOOKS = {"chemistry": "ck12_chemistry",
              "geometry": "ck12_basic_geometry_concepts",
              "algebra": "ck12_basic_algebra_concepts"}
REFERENCE_BOOKS = ["ck12_earth_science_hs", "ck12_life_science_ms", "ck12_people_physics_concepts",
                   "ck12_calculus", "ck12_basic_prob_stats_concepts"]


def pdf_lines(path):
    """Every text line of the PDF as (text, is_heading, bold_text_list)."""
    import pymupdf
    out = []
    for page in pymupdf.open(path):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in line["spans"]).strip()
                heading = all(s["font"].startswith(HEADING_FONT) for s in spans)
                # runs of consecutive bold spans = bold terms on this line
                bold, run = [], []
                for s in line["spans"]:
                    if s["flags"] & BOLD:
                        run.append(s["text"])
                    elif s["text"].strip():
                        if "".join(run).strip():
                            bold.append("".join(run).strip())
                        run = []
                if "".join(run).strip():
                    bold.append("".join(run).strip())
                out.append((text, heading, bold))
    return out


LIGATURES = {"\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff", "\ufb03": "ffi", "\ufb04": "ffl"}


def first_word(term):
    for a, b in LIGATURES.items():
        term = term.replace(a, b)
    words = [w for w in re.split(r"[\s\-'’:,.()]+", term.lower()) if w.isalpha() and len(w) > 2]
    for w in words:
        if w not in SKIP_FIRST:
            return w
    return None


def bold_terms(lines):
    """First words of the bold terms in a Vocabulary paragraph."""
    words = []
    for _, _, bold in lines:
        for term in bold:
            for part in re.split(r"[:;]", term):
                w = first_word(part)
                if w and w not in words:
                    words.append(w)
    return words


def chemistry_lessons(lines):
    lessons = []
    for i, (text, heading, _) in enumerate(lines):
        if not (heading and text == "Vocabulary"):
            continue
        j = i + 1
        while j < len(lines) and not lines[j][1]:
            j += 1
        vocab = lines[i + 1:j]
        # bold term lines only (each term is its own line)
        words = []
        for t, _, b in vocab:
            if b and " ".join(b).strip() == t:
                w = first_word(t)
                if w and w not in words:
                    words.append(w)
        k = j
        while k < len(lines) and not (lines[k][1] and lines[k][0] in ("Further Reading / Supplemental Links",
                                                                      "Review Questions", "Vocabulary")):
            k += 1
        lessons.append({"id": f"chem-{len(lessons) + 1}", "text": "\n".join(l[0] for l in lines[j:k]),
                        "first_words": words})
    return lessons


def concepts_lessons(lines, prefix):
    lessons, guidance = [], None
    for i, (text, heading, _) in enumerate(lines):
        if heading and text == "Guidance":
            guidance = i
        if heading and text == "Vocabulary" and guidance is not None:
            j = i + 1
            while j < len(lines) and not lines[j][1]:
                j += 1
            lessons.append({"id": f"{prefix}-{len(lessons) + 1}",
                            "text": "\n".join(l[0] for l in lines[guidance + 1:i]),
                            "first_words": bold_terms(lines[i + 1:j])})
            guidance = None
    return lessons


def chunks(text, size=1500):
    words = re.findall(r"[a-z]+", text.lower())
    return [set(words[k:k + size]) for k in range(0, len(words), size)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdfs", required=True)
    ap.add_argument("--out", default="evaluation/data/fresh")
    args = ap.parse_args()
    pdfs, out = Path(args.pdfs), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for name, book in TEST_BOOKS.items():
        lines = pdf_lines(pdfs / f"{book}.pdf")
        lessons = chemistry_lessons(lines) if name == "chemistry" else concepts_lessons(lines, name)
        (out / f"{name}_lessons.json").write_text(json.dumps(lessons, indent=1), encoding="utf-8")
        print(name, len(lessons), "lessons,", sum(len(l["first_words"]) for l in lessons), "key words")

    pile = {}
    for book in REFERENCE_BOOKS:
        lines = pdf_lines(pdfs / f"{book}.pdf")
        pile[book] = [sorted(c) for c in chunks("\n".join(l[0] for l in lines))]
        print(book, len(pile[book]), "chunks")
    (out / "reference_pile.json").write_text(json.dumps(pile), encoding="utf-8")


if __name__ == "__main__":
    main()


# ---------- third try (KEYNESS3_PROTOCOL.md) ----------

TEST_BOOKS_3 = {"earth_science": "ck12_earth_science_ms",
                "prob_stats": "ck12_adv_prob_stats_concepts"}
PILE_3_PDF = ["ck12_life_science_ms", "ck12_people_physics_concepts", "ck12_calculus",
              "ck12_chemistry", "ck12_basic_geometry_concepts", "ck12_basic_algebra_concepts"]


def earth_ms_lessons(lines):
    lessons = []
    for i, (text, heading, _) in enumerate(lines):
        if not (heading and text == "Vocabulary"):
            continue
        j = i + 1
        while j < len(lines) and not lines[j][1]:
            j += 1
        words = []
        for t, _, _ in lines[i + 1:j]:
            w = first_word(t.lstrip("•").strip())
            if w and w not in words:
                words.append(w)
        k = j
        while k < len(lines) and not (lines[k][1] and lines[k][0] in ("Lesson Review Questions", "Vocabulary")):
            k += 1
        lessons.append({"id": f"earth-{len(lessons) + 1}", "text": "\n".join(l[0] for l in lines[j:k]),
                        "first_words": words})
    return lessons


def build_third(pdfs, out):
    for name, book in TEST_BOOKS_3.items():
        lines = pdf_lines(pdfs / f"{book}.pdf")
        lessons = earth_ms_lessons(lines) if name == "earth_science" else concepts_lessons(lines, name)
        (out / f"{name}_lessons.json").write_text(json.dumps(lessons, indent=1), encoding="utf-8")
        print(name, len(lessons), "lessons,", sum(len(l["first_words"]) for l in lessons), "key words")
    pile = {}
    for book in PILE_3_PDF:
        lines = pdf_lines(pdfs / f"{book}.pdf")
        pile[book] = [sorted(c) for c in chunks("\n".join(l[0] for l in lines))]
    (out / "reference_pile_3.json").write_text(json.dumps(pile), encoding="utf-8")
