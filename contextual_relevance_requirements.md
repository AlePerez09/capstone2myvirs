# MyVIRS Contextual-Relevance Model Requirements

**Sprint:** 2  
**Purpose:** Define the required inputs, outputs, behavior, and constraints for the contextual-relevance component developed by Team A.

## 1. Purpose and Scope

The contextual-relevance model must identify vocabulary words that are important to the meaning of an English passage, even when those words are not the most frequent words in the passage. The model will provide a relevance signal that can later be combined with the existing frequency bands by the separate integration layer.

The ranked vocabulary words may later be translated into the learner's preferred language by another part of the MyVIRS application. Translation is not performed by the contextual-relevance model.

This requirements document covers the contextual-relevance model only. It does not define the website, user profiles, text-upload interface, translation feature, deployment, or the formula used to combine relevance with frequency.

## 2. Inputs

The model must accept:

- One passage of plain English text as a string.
- Text supplied directly to the model by another program or through the command-line prototype.
- A passage containing one or more complete sentences.

The model should handle:

- Uppercase and lowercase words.
- Common punctuation and whitespace.
- Repeated words.
- Empty or invalid input without crashing.

## 3. Outputs

The model must return an ordered list of vocabulary candidates ranked from most contextually relevant to least contextually relevant.

Each result must contain:

- `word`: the vocabulary candidate found in the passage.
- `relevance_score`: the numerical TextRank score assigned to that word.

The word's position in the ordered results represents its rank, matching the current `textrank.py` prototype without requiring changes to the team's code.

The default output should contain the top 10 ranked words when at least 10 eligible candidates exist. If fewer than 10 eligible candidates exist, the model should return every available candidate. Empty or unusable input should return an empty result or a clear validation message rather than causing the program to fail.

Example logical output:

```json
[
  {"word": "mother", "relevance_score": 0.1842},
  {"word": "cook", "relevance_score": 0.1579}
]
```

The exact technical format used to pass these results to Team B must be agreed upon during integration, but the required information above must remain available.

## 4. Functional Requirements

1. The model shall clean and tokenize the submitted English passage.
2. The model shall exclude punctuation, spaces, URLs, standalone numbers, and other unusable tokens from the candidate list.
3. The model shall use nouns, adjectives, and verbs as contextual-relevance candidates.
4. The model shall remove English stop words from the candidates.
5. The model shall create relationships between candidate words that occur near each other in the passage.
6. The current TextRank configuration shall use a four-word co-occurrence window unless testing supports a documented change.
7. The model shall use a TextRank/PageRank-style calculation to assign each candidate a relevance score.
8. The model shall rank candidates in descending order by relevance score.
9. The model shall produce repeatable results when given the same text and configuration.
10. The relevance output shall remain separate from the frequency-band output until it is processed by the integration layer.

## 5. Constraints

- **Input-language limitation:** During Sprint 2, the contextual-relevance model analyzes English passages using spaCy's `en_core_web_sm` model. The ranked vocabulary words may later be translated by another part of MyVIRS, but translation is outside the responsibility of this model.
- **Allowed data:** Testing must use public or open data, synthetic passages, or material supplied directly by the Product Owner. No real learner data will be collected.
- **Implementation boundary:** This component produces contextual-relevance scores. It does not rebuild the MyVIRS website or implement learner profiles, progress tracking, OCR, translation, or deployment.
- **Integration boundary:** Combining TextRank relevance scores with K1, K2, BAW, AWL, and `UNKNOWN` frequency categories belongs to the separate integration-layer task.
- **Candidate limitation:** The current model evaluates nouns, adjectives, and verbs. Other parts of speech are excluded unless the team documents a reason to include them.
- **Result limitation:** The current prototype returns the top 10 candidates by default.
- **Language-model dependency:** The component requires Python, spaCy, NumPy, and the `en_core_web_sm` language model.
- **Vocabulary-data limitation:** The inherited frequency file currently contains about 2,300 categorized words, so many words may be labeled `UNKNOWN` after integration.
- **Word-form limitation:** The current prototypes do not fully combine related forms such as `cell` and `cells`. The team must document any normalization or lemmatization decision before final integration.
- **Testing limitation:** The prototype has primarily been tested on short passages. Longer and more varied English passages must be evaluated before the model is considered complete.
