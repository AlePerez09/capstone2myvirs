"""
MyVIRS Sprint 2 — TextRank relevance scoring.

Adapted from Beatriz Cariello's TextRank implementation (used in her
dissertation on relevance-based vocabulary selection for Portuguese
STEM textbooks). Ported here to English using spaCy's en_core_web_sm
model. Given a passage of text, returns keywords ranked by contextual
relevance (how connected a word is to other important words in the
passage) rather than by raw frequency alone.
s
This is Team A's relevance signal. It does not yet combine with the
frequency bands from Sprint 1 (word_categories.json) — that merge is
Isa's integration layer, described in the Sprint 2 design doc.
"""

import re
from collections import OrderedDict

import numpy as np
import spacy
from spacy.lang.en.stop_words import STOP_WORDS

nlp = spacy.load("en_core_web_sm")


def pre_process_hyphenation(text):
    """Merges end-of-line hyphenated words, e.g. mole-\ncula -> molecula."""
    return re.sub(r"(\w+)-\s*(\w+)", r"\1\2", text)


def contains_digits(text):
    return any(char.isdigit() for char in text)


def get_corpus(text):
    """Cleans and tokenizes text, returning a corpus dict and ordered word list."""
    corpus = {}
    text_processed_list = []
    text_cleaned = pre_process_hyphenation(text)
    doc = nlp(text_cleaned)

    for token in doc:
        if (
            contains_digits(token.text)
            or token.is_punct
            or token.like_url
            or token.is_space
            or len(token.text) <= 2
            or "-" in token.text
        ):
            continue

        word = token.lower_
        text_processed_list.append(word)

        if word not in corpus:
            corpus[word] = {
                "part_of_speech": token.pos_,
                "lemma": token.lemma_,
                "is_stop": token.is_stop,
                "count": 1,
            }
        else:
            corpus[word]["count"] += 1

    return corpus, text_processed_list


class TextRank:
    """TextRank keyword extraction, adapted from Cariello's Portuguese implementation."""

    def __init__(self):
        self.d = 0.85
        self.min_diff = 1e-5
        self.steps = 10
        self.node_weight = None

    def analyze(self, text, candidate_pos=None, window_size=4, lower=False, stopwords=None):
        if candidate_pos is None:
            candidate_pos = ["NOUN", "ADJ", "VERB"]
        if stopwords is None:
            stopwords = []
        self._set_stopwords(stopwords)

        doc = nlp(text)
        sentences = self._sentence_segment(doc, candidate_pos, lower)
        vocab = self._get_vocab(sentences)
        token_pairs = self._get_token_pairs(window_size, sentences)
        g = self._get_matrix(vocab, token_pairs)

        pr = np.array([1] * len(vocab), dtype="float")
        previous_pr = 0

        for _ in range(self.steps):
            pr = (1 - self.d) + self.d * np.dot(g, pr)
            if abs(previous_pr - sum(pr)) < self.min_diff:
                break
            previous_pr = sum(pr)

        self.node_weight = {word: pr[i] for word, i in vocab.items()}

    def get_keywords(self, number=10):
        sorted_keywords = OrderedDict(
            sorted(self.node_weight.items(), key=lambda t: t[1], reverse=True)
        )
        return dict(list(sorted_keywords.items())[:number])

    def _set_stopwords(self, stopwords):
        for word in STOP_WORDS.union(set(stopwords)):
            nlp.vocab[word].is_stop = True

    def _sentence_segment(self, doc, candidate_pos, lower):
        ignored_words = {" ", "\n", "\t", "-", "="}
        sentences = []
        for sent in doc.sents:
            selected_words = [
                token.text.lower() if lower else token.text
                for token in sent
                if token.pos_ in candidate_pos
                and not token.is_stop
                and token.text not in ignored_words
            ]
            sentences.append(selected_words)
        return sentences

    def _get_vocab(self, sentences):
        vocab = {}
        i = 0
        for sentence in sentences:
            for word in sentence:
                if word not in vocab:
                    vocab[word] = i
                    i += 1
        return vocab

    def _get_token_pairs(self, window_size, sentences):
        return [
            (sentence[i], sentence[j])
            for sentence in sentences
            for i in range(len(sentence))
            for j in range(i + 1, min(i + window_size, len(sentence)))
        ]

    def _get_matrix(self, vocab, token_pairs):
        vocab_size = len(vocab)
        g = np.zeros((vocab_size, vocab_size), dtype="float")

        for word1, word2 in token_pairs:
            g[vocab[word1]][vocab[word2]] = 1

        g = g + g.T - np.diag(g.diagonal())
        norm = np.sum(g, axis=0)
        return np.divide(g, norm, where=norm != 0)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        sample_text = sys.argv[1]
    else:
        sample_text = """
        My mom always makes dinner after work. She loves to cook pasta and
        bake bread on the weekend. Cooking is her favorite way to relax.
        """

    tr = TextRank()
    tr.analyze(sample_text, candidate_pos=["NOUN", "ADJ", "VERB"], window_size=4)

    print("Top relevant keywords (TextRank):")
    for word, score in tr.get_keywords(10).items():
        print(f"  {word}: {score:.4f}")