"""
MyVIRS Team A: first comparison of TextRank against a frequency-only baseline.

Ground truth comes from the textbook itself. CK-12 books list each lesson's
key terms in a "Vocabulary" block and repeat them in an end-of-book
Glossary, so a ranking is better when it puts those terms near the top.
Both are removed from the text before ranking, so neither method gets to
"see" the answer key.

Rankings compared (all use the same pipeline.py pre-processing):
  raw_frequency     every kept token, ranked by count (what pipeline.py
                    prints in its "Top by frequency" column)
  frequency_only    the same candidate pool TextRank uses (nouns, adjectives,
                    verbs, no stop words or textbook stopwords), ranked by count.
                    This is the baseline: same words, frequency instead of graph.
  textrank          pipeline.textrank() exactly as committed
  textrank_converged TextRank run to convergence (the fix described in
                    approach_decision_textrank_vs_tfidf.md, section 6)

Two levels of evaluation:
  book    whole book is one input, gold = Glossary terms
  lesson  each lesson is its own passage (how MyVIRS receives text),
          gold = that lesson's Vocabulary terms

A gold "term word" is the first word of each Vocabulary/Glossary entry
(e.g. "nitrogen" for "nitrogen cycle"), because entries run straight into
their definitions with no separator, so only the first word is certain.

Usage:
    python3 compare_baseline.py --repo path/to/capstone2myvirs \
        --text path/to/biology.txt --out results/
"""

import argparse
import json
import os
import re
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.stats import wilcoxon

HEADER_RE = re.compile(
    r"^(\d+\.\d+\.?\s|www\.ck12\.org|\d+ www\.ck12\.org|Chapter \d+\.|\d+ [A-Z]|Introduction$)"
)
WRAP_LEN = 100  # lines this long or longer wrapped onto the next line
NON_TERMS = {"chapter", "lesson", "figure", "opening", "www"}


# ---------- Splitting the book into lessons, vocabulary and glossary ----------

def parse_entries(lines):
    """First word of each Vocabulary/Glossary entry, skipping wrapped lines
    and page headers/footers."""
    words = []
    prev = ""
    for line in lines:
        s = line.strip()
        if not s or HEADER_RE.match(s) or re.fullmatch(r"\d+\.\d+ [A-Z]", s):
            prev = ""
            continue
        continuation = len(prev) >= WRAP_LEN or prev.endswith("-")
        if not continuation:
            first = re.split(r"[\s(,]", s, 1)[0].lower()
            if first.isalpha() and len(first) > 2 and first not in NON_TERMS:
                words.append(first)
        prev = s
    return words


def split_book(text):
    lines = text.split("\n")
    # Glossary: the last "NN Biology Glossary" chapter heading to the end
    gloss_start = max(i for i, l in enumerate(lines) if re.fullmatch(r"\d+ \S+ Glossary", l.strip()))
    body, glossary = lines[:gloss_start], lines[gloss_start:]

    segments = []  # (vocab_words, lesson_text)
    current_vocab, current_text = None, []
    i = 0
    while i < len(body):
        if body[i].strip() == "Vocabulary":
            segments.append((current_vocab, "\n".join(current_text)))
            j = i + 1
            # Every lesson body opens with "Introduction"; the block can
            # run across a page break before that, so stop there.
            while j < len(body) and body[j].strip() != "Introduction" and j < i + 80:
                j += 1
            current_vocab = parse_entries(body[i + 1:j])
            current_text = []
            i = j
        else:
            current_text.append(body[i])
            i += 1
    segments.append((current_vocab, "\n".join(current_text)))
    return segments, parse_entries(glossary)


# ---------- Rankings ----------

def textrank_converged(sentences, window_size=4, damping=0.85, tol=1e-6, max_steps=200):
    vocab = {}
    for s in sentences:
        for w in s:
            vocab.setdefault(w, len(vocab))
    n = len(vocab)
    if n == 0:
        return {}
    rows, cols = [], []
    for s in sentences:
        for i in range(len(s)):
            for j in range(i + 1, min(i + window_size, len(s))):
                a, b = vocab[s[i]], vocab[s[j]]
                if a != b:
                    rows += [a, b]
                    cols += [b, a]
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    g.data[:] = 1.0
    col = np.asarray(g.sum(axis=0)).ravel()
    col[col == 0] = 1.0
    g = g.multiply(1.0 / col).tocsr()
    pr = np.ones(n)
    for _ in range(max_steps):
        new = (1 - damping) + damping * g.dot(pr)
        done = np.abs(new - pr).sum() < tol
        pr = new
        if done:
            break
    return {w: float(pr[i]) for w, i in vocab.items()}


def rank(scores):
    """Highest score first; ties broken alphabetically so results repeat."""
    return [w for w, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def all_rankings(pipeline, corpus, sentences):
    tr = pipeline.textrank(sentences)
    pool = set(tr)
    counts = {w: m["count"] for w, m in corpus.items()}
    return {
        "raw_frequency": rank(counts),
        "frequency_only": rank({w: counts[w] for w in pool}),
        "textrank": rank(tr),
        "textrank_converged": rank(textrank_converged(sentences)),
    }


# ---------- Metrics ----------

def precision_at(ranked, gold, k):
    top = ranked[:k]
    return sum(w in gold for w in top) / k if top else 0.0


def recall_at(ranked, gold, k):
    return sum(w in gold for w in ranked[:k]) / len(gold) if gold else 0.0


def average_precision(ranked, gold):
    hits, total = 0, 0.0
    for i, w in enumerate(ranked, 1):
        if w in gold:
            hits += 1
            total += hits / i
    return total / len(gold) if gold else 0.0


# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="folder containing pipeline.py")
    ap.add_argument("--text", required=True, help="extracted textbook text")
    ap.add_argument("--out", required=True, help="folder for results")
    args = ap.parse_args()

    sys.path.insert(0, os.path.abspath(args.repo))
    import pipeline  # loads spaCy

    os.makedirs(args.out, exist_ok=True)
    with open(args.text, encoding="utf-8") as f:
        text = f.read()
    segments, glossary_words = split_book(text)

    methods = ["raw_frequency", "frequency_only", "textrank", "textrank_converged"]
    book_corpus, book_sentences = {}, []
    lesson_rows = []

    for idx, (vocab, seg_text) in enumerate(segments):
        corpus, sentences = pipeline.build_corpus_and_sentences(seg_text)
        for w, m in corpus.items():
            if w in book_corpus:
                book_corpus[w]["count"] += m["count"]
            else:
                book_corpus[w] = dict(m)
        book_sentences.extend(sentences)
        if not vocab:
            continue
        gold = {w for w in vocab if w in corpus}
        if not gold:
            continue
        rankings = all_rankings(pipeline, corpus, sentences)
        row = {"lesson": idx, "gold_terms": len(gold), "gold_listed": len(set(vocab)),
               "words": len(corpus), "first_line": seg_text.strip().split("\n")[0][:60]}
        for m in methods:
            row[f"{m}_p@10"] = precision_at(rankings[m], gold, 10)
            row[f"{m}_r@10"] = recall_at(rankings[m], gold, 10)
            row[f"{m}_ap"] = average_precision(rankings[m], gold)
        lesson_rows.append(row)
        print(f"lesson {idx:>3}: {len(gold):>3} gold  "
              + "  ".join(f"{m[:6]} AP={row[f'{m}_ap']:.3f}" for m in methods))

    # Book level
    gold_book = {w for w in glossary_words if w in book_corpus}
    book_rankings = all_rankings(pipeline, book_corpus, book_sentences)
    ks = [10, 25, 50, 100, 250, 500, 1000]
    book = {"gold_glossary_words": len(set(glossary_words)), "gold_in_text": len(gold_book),
            "words": len(book_corpus), "candidate_pool": len(book_rankings["textrank"])}
    for m in methods:
        r = book_rankings[m]
        book[m] = {"ap": average_precision(r, gold_book),
                   **{f"p@{k}": precision_at(r, gold_book, k) for k in ks},
                   **{f"r@{k}": recall_at(r, gold_book, k) for k in ks}}
    overlap = {f"top{k}": len(set(book_rankings["textrank"][:k]) & set(book_rankings["frequency_only"][:k])) / k
               for k in ks}
    book["textrank_vs_frequency_top_k_overlap"] = overlap
    book["top20"] = {m: [(w, w in gold_book) for w in book_rankings[m][:20]] for m in methods}

    # Lesson-level summary and paired tests
    summary = {"lessons": len(lesson_rows)}
    for m in methods:
        for metric in ["p@10", "r@10", "ap"]:
            summary[f"{m}_{metric}_mean"] = float(np.mean([r[f"{m}_{metric}"] for r in lesson_rows]))
    for other in ["textrank", "textrank_converged"]:
        for metric in ["p@10", "ap"]:
            a = [r[f"{other}_{metric}"] for r in lesson_rows]
            b = [r[f"frequency_only_{metric}"] for r in lesson_rows]
            wins = sum(x > y for x, y in zip(a, b))
            losses = sum(x < y for x, y in zip(a, b))
            try:
                p = float(wilcoxon(a, b).pvalue)
            except ValueError:
                p = None
            summary[f"{other}_vs_frequency_only_{metric}"] = {"wins": wins, "losses": losses,
                                                              "ties": len(a) - wins - losses,
                                                              "wilcoxon_p": p}

    with open(os.path.join(args.out, "book_level.json"), "w") as f:
        json.dump(book, f, indent=2)
    with open(os.path.join(args.out, "lesson_level_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(args.out, "lesson_level.csv"), "w") as f:
        cols = list(lesson_rows[0].keys())
        f.write(",".join(cols) + "\n")
        for r in lesson_rows:
            f.write(",".join(f"{r[c]:.4f}" if isinstance(r[c], float) else '"' + str(r[c]).replace('"', "'") + '"'
                             if isinstance(r[c], str) else str(r[c]) for c in cols) + "\n")
    print(json.dumps({k: v for k, v in book.items() if k != "top20"}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
