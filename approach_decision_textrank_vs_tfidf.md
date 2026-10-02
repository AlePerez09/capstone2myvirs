# MyVIRS Contextual-Relevance Approach Decision: TextRank vs. TF-IDF

**Sprint:** 2  
**Status:** Accepted  
**Decision:** Use TextRank for contextual-relevance scoring. TF-IDF is documented here as a rejected alternative.  
**Related files:** `textrank.py`, `contextual_relevance_requirements.md`, `word_categories.json`

## 1. Context

MyVIRS needs a contextual-relevance signal that finds vocabulary words that matter to the meaning of a passage, "even when those words are not the most frequent words in the passage" (Requirements, Section 1). This signal is later combined with the K1, K2, BAW, AWL, and `UNKNOWN` frequency bands by the separate integration layer.

The component works under these conditions, taken from the requirements document:

- It receives **one passage at a time** as a plain English string.
- Testing may only use public, synthetic, or Product Owner–supplied text. There is **no corpus of learner texts** available.
- It must produce **repeatable results** for the same text and configuration (Functional Requirement 9).
- Its output stays **separate from the frequency bands** until integration (Functional Requirement 10).

Two common unsupervised keyword-ranking methods were considered: TextRank and TF-IDF.

## 2. Options Considered

### Option A: TextRank (chosen)

TextRank builds a graph where each candidate word (noun, adjective, or verb) is a node, and an edge connects two words that appear within a four-word window of each other. A PageRank-style calculation then scores each word by how connected it is to other well-connected words. Everything it needs comes from the passage itself.

### Option B: TF-IDF (rejected)

TF-IDF scores a word by multiplying how often it appears in a document (term frequency) by how rare it is across a collection of documents (inverse document frequency). Words that are frequent in this passage but rare elsewhere score highest.

## 3. Why TF-IDF Was Rejected

### 3.1 TF-IDF needs a reference corpus that MyVIRS does not have

The IDF half of TF-IDF only means something when there is a collection of documents to compare against. MyVIRS analyzes one passage at a time, and the project's data constraints rule out collecting learner texts to build a corpus. When TF-IDF is run on a single passage, every word gets the same IDF value, so the score reduces to plain term frequency.

The team could borrow a general-purpose corpus (for example Wikipedia), but that adds a large dataset to download, store, and maintain, and its IDF values would reflect general web text rather than the classroom and textbook passages MyVIRS targets.

### 3.2 On a single passage, TF-IDF becomes raw frequency, which the requirements explicitly ask us to go beyond

Because IDF is constant for a single document, TF-IDF ranks words by count alone. That is exactly the "most frequent words" behavior the requirements say the relevance model should improve on.

### 3.3 TF-IDF would duplicate the signal we already have

The frequency bands from `word_categories.json` are already a frequency-based signal. Adding TF-IDF would give the integration layer a second signal that is largely correlated with the first. TextRank measures something different (a word's structural position in the passage), so it adds new information for Isa's integration layer to combine.

### 3.4 TF-IDF produces large ties on short passages

Most words in a short passage appear exactly once, so TF-IDF gives them all the same score and the "ranking" falls back to whatever order the tool lists them in (alphabetical in scikit-learn). TextRank breaks many of these ties by using which words appear near each other.

### 3.5 There is direct precedent for TextRank in this exact task

The prototype is adapted from Beatriz Cariello's TextRank implementation, which was used in her dissertation for relevance-based vocabulary selection in STEM textbooks. That is the same problem MyVIRS is solving, which gives the team a tested starting point instead of building and validating a new approach from scratch.

## 4. Evidence From Side-by-Side Testing

Both methods were run on three short English passages using the same candidate filter (nouns, adjectives, verbs, stop words removed). TF-IDF was tested two ways: on the passage alone, and against a small three-passage corpus. Scores are rounded.

**Passage 1, cooking sample from `textrank.py`**

| Rank | TextRank | TF-IDF (single passage) |
|---|---|---|
| 1 | pasta (1.19) | bake (0.267) |
| 2 | bake (1.19) | bread (0.267) |
| 3 | cook (1.00) | cook (0.267) |
| 4 | bread (1.00) | cooking (0.267) |

Every TF-IDF score is identical, so its order is alphabetical. TextRank separates the cooking-related words in the second sentence from the rest.

**Passage 2, biology sample from `walking_skeleton.py`**

| Rank | TextRank | TF-IDF (single passage) |
|---|---|---|
| 1 | analyze (1.32) | analyze (0.250) |
| 2 | light (1.25) | asked (0.250) |
| 3 | convert (1.24) | biology (0.250) |
| 4 | energy (1.24) | concept (0.250) |

Again TF-IDF ties every word. Adding a three-passage corpus did not change this, because none of these words appeared in the other passages, so IDF was still equal for all of them.

**Passage 3, a longer synthetic passage about cells (repeated key term)**

| Rank | TextRank | TF-IDF (single passage) |
|---|---|---|
| 1 | cell (2.26) | cell (0.577) |
| 2 | cells (2.05) | cells (0.433) |
| 3 | animals (1.22) | animals (0.144) |
| 4 | trillions (1.09) | basic (0.144) |

When a word repeats, both methods agree on the top terms. Below that, TF-IDF goes back to ties while TextRank still differentiates.

**Takeaway:** On the kind of short, single passages MyVIRS will receive, TF-IDF either ties everything or reproduces raw frequency. TextRank produced a usable ordering in every case.

## 5. Trade-offs and Known Limitations of TextRank

Choosing TextRank does not mean it has no weaknesses. These are accepted for now and tracked as follow-ups:

- **It still favors frequent words.** A word that appears more often gets more edges, so frequency still influences TextRank scores. It is less frequency-driven than TF-IDF, not frequency-free.
- **Short passages give small graphs.** Words that share a sentence with no other candidates end up isolated and receive the same baseline score, so some ties remain.
- **Results depend on window size.** The four-word window follows Cariello's setup and Functional Requirement 6. A different window should only be adopted with documented testing.
- **Word forms are not merged.** `cell` and `cells` are ranked as separate words (see Passage 3). Lemmatization is still an open team decision.
- **No corpus-level knowledge.** TextRank cannot tell that a word is unusual in general English. That is acceptable because the frequency bands already provide that signal.

## 6. Implementation Issues Found During This Review

While testing, two problems in the current `textrank.py` were found. They do not change the decision, but they affect the scores and should be fixed in a separate story.

1. **The algorithm stops after 2 iterations instead of converging.** The convergence check compares `sum(pr)` between iterations. Because the matrix is column-normalized, that sum stays almost constant, so the loop exits on the second pass every time. Comparing the score vectors themselves (`np.abs(new_pr - pr).sum() < min_diff`) and allowing more steps fixed this. On the cells passage the corrected version converged after 37 iterations, the top 6 ranking stayed the same, and the scores shifted (for example `cell` moved from 2.26 to 2.45).
2. **`np.divide(..., where=norm != 0)` is called without `out=`.** NumPy warns that this can leave uninitialized memory in the matrix for isolated words, which is a risk to Functional Requirement 9 (repeatable results). Passing `out=np.zeros_like(g)` fixes it.

## 7. Revisit This Decision If

- The project gains a large, approved corpus of passages similar to what learners will upload. A hybrid score (TextRank combined with corpus IDF) could then be evaluated.
- Testing on longer textbook passages shows TextRank's top results are dominated by frequency anyway.
- Product Owner feedback shows learners consistently find TextRank's selected words less useful than a frequency-only list.
