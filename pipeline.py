"""
MyVIRS Team A, Sprint 3: end-to-end relevance pipeline.

Takes a CK-12 textbook PDF (or any plain text), extracts the text,
runs Beatriz Cariello's pre-processing (Appendix A) and TextRank
(Appendix B) adapted to English, and returns one record per word with
its metadata and relevance score.

Changes from the Sprint 2 textrank.py, needed to run on whole textbooks:
- Text is extracted from searchable PDFs with pypdf (no OCR).
- Long text is processed in chunks, since spaCy limits a single doc to
  about 1 million characters and a textbook is several times that.
- The word graph uses a sparse matrix. The dense matrix in the original
  code needs vocab_size squared floats, which is several GB for a
  textbook vocabulary of 15,000+ words.
- Pre-processing and TextRank share one spaCy pass instead of parsing
  the text twice.

Usage:
    python3 pipeline.py path/to/book.pdf
    python3 pipeline.py path/to/book.pdf --top 30 --out results.json
    python3 pipeline.py path/to/book.pdf --save-text book.txt
    python3 pipeline.py --text "Paste a passage here."
"""

import argparse
import json
import re
import sys

import numpy as np
import spacy
from scipy.sparse import coo_matrix

CANDIDATE_POS = {"NOUN", "ADJ", "VERB"}  # Cariello's defaults
WINDOW_SIZE = 4                          # Cariello's default
DAMPING = 0.85
MIN_DIFF = 1e-5
MAX_STEPS = 10
CHUNK_CHARS = 100_000

# Textbook layout and instruction words. Cariello's dissertation (3.5) notes
# these are frequent but pedagogically uninformative. They still get counts,
# they just never become TextRank candidates.
TEXTBOOK_STOPWORDS = {
    "chapter", "section", "lesson", "unit", "page", "pages", "figure",
    "table", "diagram", "example", "examples", "exercise", "exercises",
    "question", "questions", "answer", "answers", "review", "summary",
    "vocabulary", "objective", "objectives", "practice", "problem",
    "problems", "read", "explain", "describe", "list", "identify",
    "student", "students", "lesson", "flexbook", "ck-12", "www",
}

nlp = spacy.load("en_core_web_sm", disable=["ner"])
nlp.max_length = CHUNK_CHARS * 2


# ---------- 1. Text extraction ----------

def extract_pdf_text(pdf_path):
    """Pull the text layer out of a searchable PDF, page by page."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages)
    if len(text.strip()) < 100:
        raise ValueError(
            f"{pdf_path} has almost no extractable text. It may be a scanned PDF "
            "that needs OCR, which this pipeline does not do."
        )
    return text


# ---------- 2. Pre-processing (Appendix A) ----------

def pre_process_hyphenation(text):
    """Merges words broken across lines, e.g. 'photo-\\nsynthesis'."""
    return re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)


def contains_digits(text):
    return any(ch.isdigit() for ch in text)


def keep_token(token):
    """Appendix A's filter: drop numbers, punctuation, URLs, spaces,
    words of 2 letters or fewer, and hyphenated fragments."""
    return not (
        contains_digits(token.text)
        or token.is_punct
        or token.like_url
        or token.is_space
        or len(token.text) <= 2
        or "-" in token.text
    )


def chunk_text(text, size=CHUNK_CHARS):
    """Split long text into chunks at paragraph or sentence breaks."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind("\n", start, end)
            if cut <= start:
                cut = text.rfind(". ", start, end)
            if cut > start:
                end = cut + 1
        yield text[start:end]
        start = end


# ---------- 3. One pass: corpus metadata + TextRank sentences ----------

def build_corpus_and_sentences(text):
    corpus = {}
    sentences = []

    for doc in nlp.pipe(chunk_text(pre_process_hyphenation(text)), batch_size=4):
        for sent in doc.sents:
            candidates = []
            for token in sent:
                if not keep_token(token):
                    continue
                word = token.lower_
                entry = corpus.get(word)
                if entry is None:
                    corpus[word] = {
                        "part_of_speech": token.pos_,
                        "lemma": token.lemma_.lower(),
                        "is_stop": token.is_stop,
                        "count": 1,
                    }
                else:
                    entry["count"] += 1
                if (
                    token.pos_ in CANDIDATE_POS
                    and not token.is_stop
                    and word not in TEXTBOOK_STOPWORDS
                ):
                    candidates.append(word)
            if candidates:
                sentences.append(candidates)

    return corpus, sentences


# ---------- 4. TextRank (Appendix B, sparse) ----------

def textrank(sentences, window_size=WINDOW_SIZE):
    vocab = {}
    for sentence in sentences:
        for word in sentence:
            if word not in vocab:
                vocab[word] = len(vocab)
    n = len(vocab)
    if n == 0:
        return {}

    rows, cols = [], []
    for sentence in sentences:
        for i in range(len(sentence)):
            for j in range(i + 1, min(i + window_size, len(sentence))):
                a, b = vocab[sentence[i]], vocab[sentence[j]]
                if a != b:
                    rows += [a, b]
                    cols += [b, a]

    # Unweighted edges, as in the original: duplicates collapse to 1
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    g.data[:] = 1.0
    col_sums = np.asarray(g.sum(axis=0)).ravel()
    col_sums[col_sums == 0] = 1.0
    g = g.multiply(1.0 / col_sums).tocsr()

    pr = np.ones(n)
    previous = 0.0
    for _ in range(MAX_STEPS):
        pr = (1 - DAMPING) + DAMPING * g.dot(pr)
        if abs(previous - pr.sum()) < MIN_DIFF:
            break
        previous = pr.sum()

    return {word: float(pr[i]) for word, i in vocab.items()}


# ---------- 5. Full pipeline ----------

def analyze_text(text):
    """Text in, one record per word out, sorted by relevance."""
    corpus, sentences = build_corpus_and_sentences(text)
    scores = textrank(sentences)

    # Relevance percentile among TextRank candidates (0 lowest, 1 highest),
    # as proposed in Isa's integration layer design
    ranked = sorted(scores, key=scores.get)
    denom = max(len(ranked) - 1, 1)
    percentile = {w: i / denom for i, w in enumerate(ranked)}

    records = []
    for word, meta in corpus.items():
        records.append({
            "word": word,
            "lemma": meta["lemma"],
            "pos": meta["part_of_speech"],
            "is_stop": meta["is_stop"],
            "count": meta["count"],
            "textrank_score": round(scores[word], 6) if word in scores else None,
            "relevance": round(percentile[word], 4) if word in percentile else 0.0,
        })

    records.sort(key=lambda r: (r["relevance"], r["count"]), reverse=True)
    return records


def analyze_pdf(pdf_path):
    return analyze_text(extract_pdf_text(pdf_path))


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="MyVIRS relevance pipeline")
    parser.add_argument("pdf", nargs="?", help="path to a searchable PDF")
    parser.add_argument("--text", help="analyze this text instead of a PDF")
    parser.add_argument("--top", type=int, default=20, help="how many words to print")
    parser.add_argument("--out", help="save all records to this JSON file")
    parser.add_argument("--save-text", help="save the extracted PDF text to this file")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.pdf:
        text = extract_pdf_text(args.pdf)
        if args.save_text:
            with open(args.save_text, "w", encoding="utf-8") as f:
                f.write(text)
    else:
        parser.print_help()
        sys.exit(1)

    records = analyze_text(text)

    by_count = sorted(records, key=lambda r: r["count"], reverse=True)
    print(f"Words analyzed: {len(records)}\n")
    print(f"{'Top by relevance (score)':<32}{'Top by frequency (count)'}")
    for i in range(min(args.top, len(records))):
        r, f = records[i], by_count[i]
        score = r["textrank_score"] if r["textrank_score"] is not None else 0.0
        left = f"{r['word']} ({score:.2f})"
        right = f"{f['word']} ({f['count']})"
        print(f"{i + 1:>3}. {left:<27}{right}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(f"\nSaved {len(records)} records to {args.out}")


if __name__ == "__main__":
    main()
