from __future__ import annotations
import random
import threading
from collections import defaultdict
from ranking.embedding import Word

START = "__START__"
END = "__END__"


class PosMarkovModel:
    """
    POS trigram Markov model with optional recency decay.

    Learns (prev_pos, cur_pos) → next_pos transitions and pos → word distributions.

    decay: weight multiplier applied before each new sentence.
           1.0 = uniform weighting  |  0.95 = moderate decay  |  0.80 = aggressive
    """

    def __init__(self, decay: float = 1.0) -> None:
        if not (0.0 < decay <= 1.0):
            raise ValueError(f"decay must be in (0, 1], got {decay}")
        self._lock = threading.Lock()
        self._decay = decay
        self._transitions: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._words: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    # ── Training ──────────────────────────────────────────────────────────────

    def update(self, sentence: list[Word]) -> None:
        with self._lock:
            self._ingest(sentence)

    def train(self, sentences: list[list[Word]]) -> None:
        with self._lock:
            for sentence in sentences:
                self._ingest(sentence)

    def _ingest(self, sentence: list[Word]) -> None:
        if self._decay < 1.0:
            for dist in (*self._transitions.values(), *self._words.values()):
                for k in dist:
                    dist[k] *= self._decay

        pos_seq = [START, START] + [w.pos for w in sentence] + [END]
        for word in sentence:
            self._words[word.pos][word.actual_word] += 1.0
        for p, c, n in zip(pos_seq, pos_seq[1:], pos_seq[2:]):
            self._transitions[(p, c)][n] += 1.0

    # ── Generation ────────────────────────────────────────────────────────────

    def generate(self, max_words: int = 20, temperature: float = 1.0) -> list[str]:
        with self._lock:
            result, _ = self._generate(set(), {}, max_words, temperature)
            return result

    def generate_from_pool(
        self,
        word_pool: list[str],
        max_words: int = 20,
        temperature: float = 1.0,
        require_all: bool = False,
        max_retries: int = 100,
    ) -> list[str]:
        with self._lock:
            word_to_pos = self._word_to_pos()
            known = {w for w in word_pool if w in word_to_pos}
            if unknown := set(word_pool) - known:
                print(f"[generate_from_pool] Unknown words ignored: {unknown}")

            if not require_all:
                result, _ = self._generate(known, word_to_pos, max_words, temperature)
                return result

            best, best_remaining = [], known
            for _ in range(max_retries):
                result, remaining = self._generate(known, word_to_pos, max_words, temperature)
                if not remaining:
                    return result
                if len(remaining) < len(best_remaining):
                    best, best_remaining = result, remaining
            print(f"[generate_from_pool] Could not place all words after {max_retries} tries. Remaining: {best_remaining}")
            return best

    def _generate(
        self,
        target: set[str],
        word_to_pos: dict[str, str],
        max_words: int,
        temperature: float,
    ) -> tuple[list[str], set[str]]:
        if (START, START) not in self._transitions:
            return [], set()
        remaining, result, prev, cur = set(target), [], START, START
        while len(result) < max_words:
            nxt = self._sample(self._transitions.get((prev, cur), {}), temperature, fallback=END)
            if nxt == END:
                break
            eligible = [w for w in remaining if word_to_pos.get(w) == nxt]
            if eligible:
                dist = self._words.get(nxt, {})
                word = random.choices(eligible, weights=self._temper([dist.get(w, 0.0) for w in eligible], temperature))[0]
                remaining.discard(word)
            else:
                word = self._sample(self._words.get(nxt, {}), temperature)
            result.append(word)
            prev, cur = cur, nxt
        return result, remaining

    # ── Inspection ────────────────────────────────────────────────────────────

    def get_most_frequent_words(self, start: int = 0, end: int = 10) -> dict[str, float]:
        with self._lock:
            totals: dict[str, float] = defaultdict(float)
            for dist in self._words.values():
                for word, weight in dist.items():
                    totals[word] += weight
            return self._top(totals, start, end)

    def get_most_frequent_words_by_pos(self, start: int = 0, end: int = 10) -> dict[str, dict[str, float]]:
        with self._lock:
            return {pos: self._top(dist, start, end) for pos, dist in self._words.items()}

    @staticmethod
    def _top(dist: dict[str, float], start: int, end: int) -> dict[str, float]:
        return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True)[start:end])

    # ── Sampling ──────────────────────────────────────────────────────────────

    def _sample(self, dist: dict[str, float], temperature: float, fallback: str = "") -> str:
        if not dist:
            return fallback
        keys, weights = zip(*dist.items())
        return random.choices(keys, weights=self._temper(weights, temperature))[0]

    def _word_to_pos(self) -> dict[str, str]:
        best: dict[str, tuple[str, float]] = {}
        for pos, dist in self._words.items():
            for word, weight in dist.items():
                if word not in best or weight > best[word][1]:
                    best[word] = (pos, weight)
        return {word: pos for word, (pos, _) in best.items()}

    @staticmethod
    def _temper(weights, temperature: float) -> list[float]:
        t = max(0.01, temperature)
        return [w ** (1.0 / t) for w in weights]