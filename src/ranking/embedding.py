import spacy
from spacy.tokens import Doc
from dataclasses import dataclass

@dataclass(frozen=True)
class Word:
    actual_word: str
    pos: str


class PosEmbeddingProvider:
    """Wrapper around spaCy POS tagger that works with pre-tokenized input (e.g. WhisperX tokens)."""

    def __init__(self) -> None:
        self.nlp = spacy.load("en_core_web_sm")

    def as_words_with_class(self, tokens: list[str]) -> list[Word]:
        """
        tokens must be pre-tokenized (e.g. WhisperX output).
        No re-tokenization is performed.
        """

        doc = Doc(self.nlp.vocab, words=tokens)

        for name, component in self.nlp.pipeline:
            print(name)
            doc = component(doc)

        return [
            Word(token.text, token.pos_)
            for token in doc
            if token.pos_ not in ("PUNCT", "SPACE", "SYM")
        ]