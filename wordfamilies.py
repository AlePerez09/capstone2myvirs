"""
MyVIRS Team A, Sprint 3: group word forms into word families.

Eric's lists count word families, not single word forms: walk, walks,
walked, walker, non-walker and unwalked all count as "walk". spaCy's
lemmatizer only removes inflections (-s, -ed, -ing), so it groups
"cells" with "cell" but leaves "development", "protective" and
"nonliving" on their own. This module maps every word to a family
headword in three steps, in the order Isa's integration layer design
proposes, and records which step matched:

  1. family_list  A word family list file, if one is supplied: the
                  authors' own word family lists (available from Ehsan on
                  request) or Nation's BNC/COCA families. Most accurate.
  2. derived      Conservative derivational rules (development -> develop,
                  activity -> active, nonliving -> living -> live), applied
                  only when the base word also appears in the text, so we
                  never invent a headword.
  3. lemma        spaCy's lemma (cells -> cell, protected -> protect).

A word that none of these change is its own headword ("self").

Known gaps without a family list: "-er" nouns (walker) are not merged,
because "flower -> flow" and "layer -> lay" would be wrong more often
than right, and irregular derivations (decision -> decide) are missed.
Loading a family list fixes both.

Family list format (Nation's BNC/COCA files use this):
    walk
    	walks
    	walked
    	walker
A headword starts at the beginning of a line, its members are indented.
A two-column CSV ("word,headword") also works.
"""

import csv
import os

# spaCy lemmatizes these wrongly (species -> specie, physics -> physic)
KEEP_AS_IS = {
    "species", "series", "means", "news", "physics", "mathematics",
    "economics", "genetics", "ethics", "data", "lens", "gas", "bias",
    "virus", "status", "basis", "analysis", "hypothesis", "nucleus",
    "fungus", "focus", "chaos", "process", "class", "glass", "mass",
}

# (suffix, replacements to try in order). A rule fires only if the
# resulting base appears in the text and is at least MIN_BASE letters long.
SUFFIX_RULES = [
    ("iness", ["y"]),            # happiness -> happy
    ("ness", [""]),              # darkness -> dark
    ("ment", [""]),              # development -> develop
    ("ility", ["le"]),           # ability -> able
    ("ity", ["", "e"]),          # electricity -> electric, activity -> active
    ("ation", ["e", "", "ate"]),  # formation -> form, creation -> create
    ("ition", ["", "e"]),        # addition -> add, definition -> define
    ("ion", ["", "e"]),          # protection -> protect, reduction -> reduce
    ("ically", ["ic"]),          # basically -> basic
    ("ily", ["y"]),              # easily -> easy
    ("ly", ["", "e"]),           # quickly -> quick, simply -> simple
    ("ful", [""]),               # harmful -> harm
    ("less", [""]),              # harmless -> harm
    ("ive", ["", "e"]),          # protective -> protect, active -> act
    ("able", ["", "e"]),         # predictable -> predict
    ("ible", ["", "e"]),         # reversible -> reverse
]
# Words the suffix rules would get wrong, kept as their own headword
NOT_DERIVED = {
    "early", "only", "family", "apply", "supply", "reply", "belly", "fly",
    "station", "nation", "ration", "lotion", "motion", "mention", "action",
    "lesson", "season", "reason", "person", "million", "billion", "onion",
    "ability", "city", "unity", "university", "community", "native",
    "element", "comment", "moment", "segment", "cement", "ailment",
    "unless", "table", "cable", "noble", "under", "until", "union",
}
PER_RULE_MIN = {"ly": 4, "ive": 4}   # stops early -> ear, native -> nat
PREFIX_RULES = ["non", "un"]     # nonliving -> living, unknown -> known
MIN_BASE = 3
MIN_PREFIX_BASE = 4              # keeps union -> ion, until -> til out


def load_family_list(path):
    """Read a word family list into {member: headword}."""
    mapping = {}
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    mapping[row[0].strip().lower()] = row[1].strip().lower()
        return mapping

    headword = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            if not raw.strip():
                continue
            word = raw.strip().split()[0].lower()
            if raw[0] in " \t":
                if headword:
                    mapping[word] = headword
            else:
                headword = word
                mapping[word] = headword
    return mapping


class FamilyResolver:
    """Maps word forms to family headwords for one text."""

    def __init__(self, corpus, family_list=None):
        """corpus: the {word: {"lemma": ..., ...}} dict from pre-processing.
        family_list: optional {member: headword} from load_family_list()."""
        self.corpus = corpus
        self.family_list = family_list or {}
        self.known = set(corpus) | {m["lemma"] for m in corpus.values()}
        self._cache = {}

    def resolve(self, word):
        """Return (headword, match_source)."""
        if word not in self._cache:
            self._cache[word] = self._resolve(word, depth=0)
        return self._cache[word]

    def _lemma(self, word):
        if word in KEEP_AS_IS or word.endswith("ics"):
            return word
        meta = self.corpus.get(word)
        lemma = meta["lemma"] if meta else word
        if not (lemma.isalpha() and len(lemma) >= 2):
            lemma = word
        # Plural fallback for words spaCy left alone (e.g. tagged as proper
        # nouns): "cells" -> "cell" when "cell" also appears in the text
        if lemma == word and len(word) > 3 and not word.endswith("ss"):
            for suffix, rep in (("ies", "y"), ("es", ""), ("s", "")):
                base = word[: -len(suffix)] + rep
                if word.endswith(suffix) and base in self.corpus:
                    return base
        return lemma

    def _strip(self, word):
        """One derivational step, or None."""
        for prefix in PREFIX_RULES:
            base = word[len(prefix):]
            if word.startswith(prefix) and len(base) >= MIN_PREFIX_BASE and base in self.known:
                return base
        if word in NOT_DERIVED:
            return None
        for suffix, replacements in SUFFIX_RULES:
            if word.endswith(suffix):
                min_base = PER_RULE_MIN.get(suffix, MIN_BASE)
                stem = word[: -len(suffix)]
                for rep in replacements:
                    base = stem + rep
                    if len(base) >= min_base and base != word and base in self.known:
                        return base
        return None

    def _resolve(self, word, depth):
        if word in self.family_list:
            return self.family_list[word], "family_list"

        lemma = self._lemma(word)
        if lemma in self.family_list:
            return self.family_list[lemma], "family_list"

        if depth < 3:
            base = self._strip(lemma)
            if base:
                head, _ = self._resolve(base, depth + 1)
                return head, "derived"

        if lemma != word:
            return lemma, "lemma"
        return word, "self"


def group_by_family(corpus, family_list=None):
    """Collapse a pre-processing corpus into one entry per headword.

    Returns (families, word_to_head) where families is
    {headword: {"forms": [...], "count": n, "pos": ..., "match_source": ...}}.
    """
    resolver = FamilyResolver(corpus, family_list)
    families, word_to_head = {}, {}

    for word, meta in corpus.items():
        head, source = resolver.resolve(word)
        word_to_head[word] = head
        fam = families.setdefault(head, {"forms": [], "count": 0, "pos_counts": {},
                                         "match_source": "self", "is_stop": True})
        fam["forms"].append(word)
        fam["count"] += meta["count"]
        fam["pos_counts"][meta["part_of_speech"]] = (
            fam["pos_counts"].get(meta["part_of_speech"], 0) + meta["count"]
        )
        fam["is_stop"] = fam["is_stop"] and meta["is_stop"]
        # Report the strongest source among the family's members
        order = ["self", "lemma", "derived", "family_list"]
        if order.index(source) > order.index(fam["match_source"]):
            fam["match_source"] = source

    for fam in families.values():
        fam["pos"] = max(fam["pos_counts"], key=fam["pos_counts"].get)
        fam["forms"].sort(key=lambda w: -corpus[w]["count"])
        del fam["pos_counts"]

    return families, word_to_head


def find_family_list(path=None):
    """Use an explicit path, or data/word_families.txt / .csv if present."""
    if path:
        return load_family_list(path)
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("word_families.txt", "word_families.csv"):
        candidate = os.path.join(here, "data", name)
        if os.path.exists(candidate):
            return load_family_list(candidate)
    return None
