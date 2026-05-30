from __future__ import annotations

import random
import threading
from collections import defaultdict

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

    Args:
        decay: Multiplicative factor applied to all existing counts before each
               new sentence is ingested. Values below 1.0 cause older observations
               to lose influence relative to newer ones.

               Examples:
                 1.00 = no decay (uniform weighting, original behaviour)
                 0.99 = gentle decay; suits large, slowly-changing corpora
                 0.95 = moderate decay; good default for streaming updates
                 0.80 = aggressive decay; model nearly forgets old data quickly
    """

    def __init__(self, decay: float = 1.0) -> None:
        if not (0.0 < decay <= 1.0):
            raise ValueError(f"decay must be in (0, 1], got {decay}")

        self._lock = threading.Lock()
        self._decay = decay

        # (prev_pos, current_pos) -> {next_pos: weight}
        self._pos_transitions: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # POS -> {word: weight}
        self._word_distributions: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    # ------------------------------------------------------------------
    # Public training API
    # ------------------------------------------------------------------

    def update(self, sentence: list[Word]) -> None:
        """Ingest a single sentence, applying recency decay first."""
        with self._lock:
            self._apply_decay()
            self._update(sentence)

    def train(self, sentences: list[list[Word]]) -> None:
        """Ingest multiple sentences, applying decay before each one."""
        with self._lock:
            for sentence in sentences:
                self._apply_decay()
                self._update(sentence)

    # ------------------------------------------------------------------
    # Public generation API
    # ------------------------------------------------------------------

    def generate(self, max_words: int = 20, temperature: float = 1.0) -> list[str]:
        """Generate a sentence using the learnt POS trigram model."""
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
        Generate a sentence biased toward a given word pool.

        If *require_all* is True the method retries up to *max_retries* times,
        returning the attempt that managed to place the most pool words.
        """
        with self._lock:
            if (START, START) not in self._pos_transitions:
                return []

            word_to_pos = self._build_word_to_pos_map()

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
                        next_pos, remaining, word_to_pos, temperature
                    )

                    if word:
                        remaining.discard(word)
                    else:
                        word = self._sample_word(next_pos, temperature)

                    result.append(word)
                    prev_pos, current_pos = current_pos, next_pos

                return result, remaining

            if not require_all:
                return attempt()[0]

            best_result: list[str] = []
            best_remaining: set[str] = target_words

            for _ in range(max_retries):
                result, remaining = attempt()

                if not remaining:
                    return result

                if len(remaining) < len(best_remaining):
                    best_result, best_remaining = result, remaining

            print(
                f"[generate_from_pool] Could not place all words after {max_retries} "
                f"tries. Remaining: {best_remaining}"
            )
            return best_result

    # ------------------------------------------------------------------
    # Public inspection helpers
    # ------------------------------------------------------------------

    def get_most_frequent_words(self, start: int = 0, end: int = 10) -> dict[str, float]:
        with self._lock:
            total: dict[str, float] = defaultdict(float)
            for dist in self._word_distributions.values():
                for word, weight in dist.items():
                    total[word] += weight
            return dict(sorted(total.items(), key=lambda kv: kv[1], reverse=True)[start:end])
 
    def get_most_frequent_words_by_pos(
        self, start: int = 0, end: int = 10
    ) -> dict[str, dict[str, float]]:
        with self._lock:
            return {
                pos: dict(
                    sorted(dist.items(), key=lambda kv: kv[1], reverse=True)[start:end]
                )
                for pos, dist in self._word_distributions.items()
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_decay(self) -> None:
        """
        Scale all stored weights by *decay*.

        Called once per sentence ingested, so older observations lose influence
        relative to freshly added ones.  No-op when decay is exactly 1.0.
        """
        if self._decay == 1.0:
            return

        for inner in self._pos_transitions.values():
            for key in inner:
                inner[key] *= self._decay

        for inner in self._word_distributions.values():
            for key in inner:
                inner[key] *= self._decay

    def _update(self, sentence: list[Word]) -> None:
        """Build trigram POS transitions from a single sentence."""
        pos_sequence = [START, START]

        for word in sentence:
            self._word_distributions[word.pos][word.actual_word] += 1.0
            pos_sequence.append(word.pos)

        pos_sequence.append(END)

        for prev_pos, current_pos, next_pos in zip(
            pos_sequence,
            pos_sequence[1:],
            pos_sequence[2:],
        ):
            self._pos_transitions[(prev_pos, current_pos)][next_pos] += 1.0

    def _sample_next_pos(self, prev_pos: str, current_pos: str, temperature: float) -> str:
        """Sample the next POS tag from the trigram transition distribution."""
        candidates = self._pos_transitions.get((prev_pos, current_pos), {})

        if not candidates:
            return END

        positions = list(candidates.keys())
        weights = self._apply_temperature(list(candidates.values()), temperature)

        return random.choices(positions, weights=weights, k=1)[0]

    def _sample_word(self, pos: str, temperature: float) -> str:
        """Sample a surface form for the given POS tag."""
        candidates = self._word_distributions.get(pos, {})

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
        Pick a word from *remaining* that matches *pos*, weighted by its
        learnt frequency (after decay).  Returns None when no eligible word
        exists.
        """
        dist = self._word_distributions.get(pos, {})
        eligible = [w for w in remaining if word_to_pos.get(w) == pos]

        if not eligible:
            return None

        weights = [dist.get(w, 0.0) for w in eligible]

        return random.choices(
            eligible,
            weights=self._apply_temperature(weights, temperature),
            k=1,
        )[0]

    def _build_word_to_pos_map(self) -> dict[str, str]:
        """
        Reverse lookup: word -> POS.

        When a word appears under multiple POS tags (e.g. "run" as NN and VB),
        the tag with the highest current weight wins.
        """
        mapping: dict[str, str] = {}
        best_weight: dict[str, float] = {}

        for pos, dist in self._word_distributions.items():
            for word, weight in dist.items():
                if weight > best_weight.get(word, -1.0):
                    mapping[word] = pos
                    best_weight[word] = weight

        return mapping

    @staticmethod
    def _apply_temperature(weights: list[float], temperature: float) -> list[float]:
        return [w ** (1.0 / max(0.01, temperature)) for w in weights]
    