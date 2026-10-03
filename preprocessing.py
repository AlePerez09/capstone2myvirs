import re
import spacy

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
