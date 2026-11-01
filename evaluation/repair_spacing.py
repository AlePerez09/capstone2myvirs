"""
MyVIRS Team A, Sprint 4: put the missing spaces back into data/trigonometry.txt.

The committed trigonometry.txt was extracted with most spaces missing
("willreviewsomeimportantaspectsoftriangles"). About half of its letters
are in run-together "words" of 20+ letters, so the pipeline would treat
whole sentences as single tokens. Biology does not have this problem.

This script re-splits run-together text with the standard dictionary
method (the most probable split under English word frequencies, the same
idea as the wordninja library). Word frequencies come from the wordfreq
package (pip install wordfreq), top 200,000 English words. Math words the
book spells out with spaces around them are added too, so terms like
"cosecant" are known.

A letter run stays whole unless a split is more probable (so "atriangle"
splits but "measurement" doesn't), and each extra word in a split costs a
small penalty, so splits stay conservative.
It is a repair, not a perfect extraction: a few splits will be wrong. A
clean re-extraction from the PDF would be better if one is available.

Usage:
    python3 evaluation/repair_spacing.py data/trigonometry.txt evaluation/data/trigonometry_spaced.txt
"""

import math
import re
import sys
from collections import Counter
from pathlib import Path

from wordfreq import top_n_list, word_frequency

MAX_WORD = 22
WORD_PENALTY = 2.0     # discourages splitting into many short pieces
MIN_FREQ = 1e-9
WORD_COMMON = -math.log(1e-5)  # frequent enough to be the real word
WORD_RARE = -math.log(1e-7)    # rare enough to be a glitch
WORD_RE = re.compile(r"[A-Za-z]+")
# Single letters are mostly variables in a math book; "a" and "i" are words
SINGLE_LETTERS_OK = {"a", "i", "x", "y"}
# General trigonometry vocabulary that wordfreq has no frequency for. Without
# these, "coterminal" would be split into "co terminal".
MATH_TERMS = {"coterminal", "quadrantal", "cofunction", "cofunctions", "arcsine",
              "arccosine", "arctangent", "sinusoidal", "limacon", "limacons"}


def build_costs(raw_text):
    freq = {}
    for w in top_n_list("en", 200_000):
        if w.isalpha() and (len(w) > 1 or w in SINGLE_LETTERS_OK):
            freq[w] = word_frequency(w, "en")
    # Rare real words the book uses (cosecant, clinometer) that fall outside
    # the top 200,000 but are still in wordfreq's data. Skipped when the word
    # is just common words glued together ("sinx", "graphis", "leftside").
    top = {w: -math.log(f) for w, f in freq.items() if f > 0}
    pre = Splitter(top)
    for w in set(t.lower() for t in WORD_RE.findall(raw_text)):
        if w not in freq and 4 <= len(w) <= MAX_WORD:
            f = word_frequency(w, "en")
            parts = pre.split(w)
            glued = len(parts) > 1 and all(word_frequency(x, "en") > 1e-6 or len(x) == 1 for x in parts)
            if f > 0 and not glued:
                freq[w] = f
    # Standard trigonometry terms wordfreq has no count for at all
    for w in MATH_TERMS:
        freq.setdefault(w, 1e-7)
    costs = {w: -math.log(max(f, MIN_FREQ)) for w, f in freq.items() if len(w) <= MAX_WORD}
    # Words the book prints 3+ times that wordfreq lacks, unless they are two
    # known words glued together ("atriangle", "inthislesson")
    base = Splitter(costs)
    for w, c in Counter(t.lower() for t in WORD_RE.findall(raw_text)).items():
        if w not in costs and 4 <= len(w) <= 14 and c >= 3 and len(base.split(w)) == 1:
            costs[w] = -math.log(1e-6)
    return costs


class Splitter:
    def __init__(self, costs):
        self.cost = costs
        self.unknown = -math.log(MIN_FREQ) * 2  # per letter of an unknown chunk

    def word_cost(self, w):
        c = self.cost.get(w)
        if c is None:
            c = self.unknown * len(w)
        return c + WORD_PENALTY

    def split(self, s):
        low = s.lower()
        n = len(low)
        best = [0.0] + [math.inf] * n
        back = [0] * (n + 1)
        for i in range(1, n + 1):
            for j in range(max(0, i - MAX_WORD), i):
                piece = low[j:i]
                if i == n and len(piece) == 1 and piece not in self.cost:
                    # a one-letter variable at the end of a run: "thefunctionc (x)"
                    c = best[j] + WORD_COMMON + WORD_PENALTY
                else:
                    c = best[j] + self.word_cost(piece)
                if c < best[i]:
                    best[i], back[i] = c, j
        parts, i = [], n
        while i > 0:
            parts.append(s[back[i]:i])  # keep original capitalization
            i = back[i]
        return parts[::-1]


def repair(text, splitter):
    text = text.replace("\r\n", "\n")
    # Rejoin words broken across lines first ("func-\ntionisaparent"), the same
    # way pipeline.pre_process_hyphenation does, so the splitter sees whole words
    text = re.sub(r"([A-Za-z]+)-[ \t]*\n[ \t]*([a-z]+)", r"\1\2\n", text)
    # Numbers glued to words: "a3-sided", "with2equal", "selling177units"
    text = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z]{2})", " ", text)
    # Missing space after punctuation: "x.Dependent", "angles,and", "clock.)Given"
    text = re.sub(r"([a-z][.,;:)])([A-Za-z]{2})", r"\1 \2", text)
    text = re.sub(r"([a-z])\(", r"\1 (", text)

    def fix(m):
        w = m.group(0)
        if len(w) < 4:
            return w
        # Two common words glued into a rare "word": "sinewave", "straightline"
        if splitter.cost.get(w.lower(), 99) > WORD_RARE:
            for k in range(3, len(w) - 2):
                a, b = w[:k].lower(), w[k:].lower()
                if splitter.cost.get(a, 99) < WORD_COMMON and splitter.cost.get(b, 99) < WORD_COMMON:
                    return w[:k] + " " + w[k:]
        parts = splitter.split(w)  # a known word stays whole unless a split is likelier
        return " ".join(parts) if len(parts) > 1 else w

    return WORD_RE.sub(fix, text)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    raw = Path(src).read_text(encoding="utf-8")
    fixed = repair(raw, Splitter(build_costs(raw)))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(fixed, encoding="utf-8")
    before = [w for w in WORD_RE.findall(raw) if len(w) >= 20]
    after = [w for w in WORD_RE.findall(fixed) if len(w) >= 20]
    print(f"letter runs of 20+ letters: {len(before)} before, {len(after)} after")


if __name__ == "__main__":
    main()
