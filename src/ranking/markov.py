from __future__ import annotations

import random

from collections import Counter, defaultdict
import threading

from ranking.embedding import Word


START = "__START__"
END = "__END__"


class PosMarkovModel:
    """
    Frequency-weighted POS-based Markov language model.

    Learns:
        POS -> next POS transitions

    And:
        POS -> word frequencies

    Example:
        DET -> NOUN -> VERB

    Then realizes actual words from each POS bucket.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._transitions: dict[str, Counter[str]] = defaultdict(Counter) # Current POS -> next POS counts
        self._words_by_pos: dict[str, Counter[str]] = defaultdict(Counter) # POS -> word frequency counts


    def update(self, words: list[Word]) -> None:
        """ Retrain the model with a single new sentence """
        with self._lock: self._update(words)

    def train(self, sentences: list[list[Word]]) -> None:
        """ Train model on multiple sentences """
        with self._lock: [self._update(sentence) for sentence in sentences]

    def generate(self, max_words: int = 20, temperature: float = 1.0) -> list[str]:
        """
        Generate a sentence.

        temperature:
            < 1.0 -> more predictable
            = 1.0 -> normal
            > 1.0 -> more random
        """
        with self._lock:
            if START not in self._transitions:
                return []

            result: list[str] = []
            current_pos = START

            while len(result) < max_words:
                next_pos = self._sample_next_pos(current_pos, temperature)

                if next_pos == END:
                    break

                result.append(self._sample_word(next_pos, temperature))
                current_pos = next_pos

            return result
        
    def generate_from_pool(
        self,
        word_pool: list[str],
        max_words: int = 20,
        temperature: float = 1.0,
        require_all: bool = False,
        max_retries: int = 100,
    ) -> list[str]:
        """
        Generate a sentence that draws words from word_pool wherever the POS
        sequence allows it, falling back to normal sampling otherwise.

        Args:
            word_pool:    Our vocabulary from our actual top_k words that we want to use (and for which we have recordings)
            require_all:  If True, retry until every pool word appears in the
                        sentence (may not be achievable bc it may not actually converge(?)).
            max_retries:  Guard against infinite loops when require_all=True.
        """
        with self._lock:
            if START not in self._transitions:
                return []

            # Build word -> POS reverse lookup once
            word_to_pos: dict[str, str] = {
                word: pos
                for pos, counter in self._words_by_pos.items()
                for word in counter
            }

            # Warn about unknown words so callers (me) aren't (me) confused
            unknown = [w for w in word_pool if w not in word_to_pos]
            if unknown:
                # Why I'm not just passing a logger is beyond me like what I don't have the time?
                # I have the time to write this?!?!
                print(f"[generate_from_pool] Words not in model, will be skipped: {unknown}")

            pool = set(word_pool) - set(unknown)

            def _attempt() -> tuple[list[str], set[str]]:
                pending = set(pool) # pool words not yet placed
                result: list[str] = []
                current_pos = START

                while len(result) < max_words:
                    next_pos = self._sample_next_pos(current_pos, temperature)
                    if next_pos == END:
                        break

                    # Pool words that are still pending AND fit this POS slot
                    eligible = [w for w in pending if word_to_pos[w] == next_pos]

                    if eligible:
                        weights = [self._words_by_pos[next_pos][w] for w in eligible]
                        chosen = random.choices(
                            eligible,
                            weights=self._apply_temperature(weights, temperature),
                            k=1,
                        )[0]
                        pending.discard(chosen)
                    else:
                        chosen = self._sample_word(next_pos, temperature)

                    result.append(chosen)
                    current_pos = next_pos

                return result, pending

            if not require_all:
                result, _ = _attempt()
                return result

            # Retry until all pool words are placed (best-effort)
            best_result: list[str] = []
            best_pending: set[str] = pool

            for _ in range(max_retries):
                result, pending = _attempt()
                if not pending:
                    return result
                if len(pending) < len(best_pending):   # track closest attempt
                    best_result, best_pending = result, pending

            print(f"[generate_from_pool] Could not place all words after {max_retries} retries. "
                f"Unplaced: {best_pending}")
            return best_result
        
    def get_most_frequent_words(self, start: int = 0, end: int = 10) -> dict[str, int]:
        with self._lock:
            total = Counter()
            for counter in self._words_by_pos.values():
                total.update(counter)
            return dict(total.most_common(end)[start:])

    def get_most_frequent_words_by_pos(self, start: int = 0, end: int = 10) -> dict[str, dict[str, int]]:
        with self._lock:
            return {
                pos: dict(counter.most_common(end)[start:])
                for pos, counter in self._words_by_pos.items()
            }
        
    
    def _update(self, words: list[Word]) -> None:
        """ Update "weights" with a single sentence """
        if isinstance(words, str):
            raise TypeError(f"Expected list[Word], got a raw string: {words!r}")
        
        pos_sequence = [START]

        for word in words:
            self._words_by_pos[word.pos][word.actual_word] += 1
            pos_sequence.append(word.pos)

        pos_sequence.append(END)

        for current_pos, next_pos in zip(
            pos_sequence,
            pos_sequence[1:],
        ):
            self._transitions[current_pos][next_pos] += 1

    def _sample_next_pos(self, current_pos: str, temperature: float) -> str:
        candidates = self._transitions[current_pos]
        positions = list(candidates.keys())

        return random.choices(
            positions,
            weights=self._apply_temperature(list(candidates.values()), temperature),
            k=1,
        )[0]

    def _sample_word(self, pos: str, temperature: float) -> str:
        candidates = self._words_by_pos[pos]
        words = list(candidates.keys())

        return random.choices(
            words,
            weights=self._apply_temperature(list(candidates.values()), temperature),
            k=1,
        )[0]

    @staticmethod
    def _apply_temperature(weights: list[int], temperature: float) -> list[float]:
        return [
            weight ** (1.0 / max(0.01, temperature))
            for weight in weights
        ]