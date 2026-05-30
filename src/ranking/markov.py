from __future__ import annotations

import random
import threading
from collections import Counter, defaultdict

from ranking.embedding import Word


START = "__START__"
END = "__END__"


class PosMarkovModel:
    """
    POS trigram Markov model.

    Learns:
        (prev_pos, current_pos) -> next_pos

    Also tracks:
        POS -> word frequencies
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # (prev_pos, current_pos) -> Counter(next_pos)
        self._pos_transitions: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

        # POS -> Counter(words)
        self._word_distributions: dict[str, Counter[str]] = defaultdict(Counter)

    def update(self, sentence: list[Word]) -> None:
        """Update with a single sentence."""
        with self._lock:
            self._update(sentence)

    def train(self, sentences: list[list[Word]]) -> None:
        """ Train on multiple sentences."""
        with self._lock:
            for sentence in sentences:
                self._update(sentence)

    def _update(self, sentence: list[Word]) -> None:
        """ Build trigram POS transitions from a sentence """
        pos_sequence = [START, START]

        for word in sentence:
            self._word_distributions[word.pos][word.actual_word] += 1
            pos_sequence.append(word.pos)

        pos_sequence.append(END)

        for prev_pos, current_pos, next_pos in zip(
            pos_sequence,
            pos_sequence[1:],
            pos_sequence[2:],
        ):
            self._pos_transitions[(prev_pos, current_pos)][next_pos] += 1

    def generate(self, max_words: int = 20, temperature: float = 1.0) -> list[str]:
        """Generate a sentence"""
        with self._lock:
            if (START, START) not in self._pos_transitions:
                return []

            words: list[str] = []
            prev_pos, current_pos = START, START

            while len(words) < max_words:
                next_pos = self._sample_next_pos(prev_pos, current_pos, temperature)

                if next_pos == END:
                    break

                words.append(self._sample_word(next_pos, temperature))
                prev_pos, current_pos = current_pos, next_pos

            return words

    def generate_from_pool(
        self,
        word_pool: list[str],
        max_words: int = 20,
        temperature: float = 1.0,
        require_all: bool = False,
        max_retries: int = 100,
    ) -> list[str]:
        """
        Generate sentences biased toward a given word pool.

        If require_all=True, tries to include every pool word.
        """

        with self._lock:
            if (START, START) not in self._pos_transitions:
                return []

            word_to_pos = self._build_word_to_pos_map()

            # Filter unknown words
            unknown_words = [w for w in word_pool if w not in word_to_pos]
            if unknown_words:
                print(f"[generate_from_pool] Unknown words ignored: {unknown_words}")

            target_words = set(word_pool) - set(unknown_words)

            def attempt() -> tuple[list[str], set[str]]:
                remaining = set(target_words)
                result: list[str] = []

                prev_pos, current_pos = START, START

                while len(result) < max_words:
                    next_pos = self._sample_next_pos(prev_pos, current_pos, temperature)

                    if next_pos == END:
                        break

                    word = self._select_word_for_pos(
                        next_pos,
                        remaining,
                        word_to_pos,
                        temperature,
                    )

                    if word:
                        remaining.discard(word)
                    else:
                        word = self._sample_word(next_pos, temperature)

                    result.append(word)
                    prev_pos, current_pos = current_pos, next_pos

                return result, remaining

            # Simple generation mode
            if not require_all:
                return attempt()[0]

            # Best-effort retry loop
            best_result: list[str] = []
            best_remaining: set[str] = target_words

            for _ in range(max_retries):
                result, remaining = attempt()

                if not remaining:
                    return result

                if len(remaining) < len(best_remaining):
                    best_result, best_remaining = result, remaining

            print(
                f"[generate_from_pool] Could not place all words after {max_retries} tries. "
                f"Remaining: {best_remaining}"
            )
            return best_result

    def _sample_next_pos(self, prev_pos: str, current_pos: str, temperature: float) -> str:
        """
        Sample next POS from trigram transition distribution.
        """
        candidates = self._pos_transitions[(prev_pos, current_pos)]

        if not candidates:
            return END

        positions = list(candidates.keys())
        weights = self._apply_temperature(list(candidates.values()), temperature)

        return random.choices(positions, weights=weights, k=1)[0]

    def _sample_word(self, pos: str, temperature: float) -> str:
        """
        Sample a word given a POS.
        """
        candidates = self._word_distributions[pos]

        if not candidates:
            return ""

        words = list(candidates.keys())
        weights = self._apply_temperature(list(candidates.values()), temperature)

        return random.choices(words, weights=weights, k=1)[0]

    def _select_word_for_pos(
        self,
        pos: str,
        remaining: set[str],
        word_to_pos: dict[str, str],
        temperature: float,
    ) -> str | None:
        """
        Try to pick a pool word that matches the required POS.
        """
        eligible = [w for w in remaining if word_to_pos[w] == pos]

        if not eligible:
            return None

        weights = [self._word_distributions[pos][w] for w in eligible]

        return random.choices(
            eligible,
            weights=self._apply_temperature(weights, temperature),
            k=1,
        )[0]

    def _build_word_to_pos_map(self) -> dict[str, str]:
        """
        Reverse lookup: word -> POS (best-effort, last-write-wins).
        """
        mapping: dict[str, str] = {}

        for pos, counter in self._word_distributions.items():
            for word in counter:
                mapping[word] = pos

        return mapping

    @staticmethod
    def _apply_temperature(weights: list[int], temperature: float) -> list[float]:
        return [w ** (1.0 / max(0.01, temperature)) for w in weights]


    def get_most_frequent_words(self, start: int = 0, end: int = 10) -> dict[str, int]:
        with self._lock:
            total = Counter()
            for counter in self._word_distributions.values():
                total.update(counter)
            return dict(total.most_common(end)[start:])

    def get_most_frequent_words_by_pos(self, start: int = 0, end: int = 10) -> dict[str, dict[str, int]]:
        with self._lock:
            return {
                pos: dict(counter.most_common(end)[start:])
                for pos, counter in self._word_distributions.items()
            }