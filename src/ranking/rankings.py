from collections import defaultdict
import threading

from ranking.embedding import Word
from util.logger import Logger


class Rankings:
    """
    Our in memory ranking system.
    """

    def __init__(self, logger: Logger) -> None:
        self._counts: dict[Word, int] = defaultdict(int)
        self._is_sorted = False
        self._lock = threading.Lock()

        self.logger = logger

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._counts) == 0

    def _update(self, words: list[Word]) -> None:
        """Count incoming strings and merge them into the live rankings."""
        for word in words:
            self._counts[word] += 1

        self._is_sorted = False

    def update(self, words: list[Word]) -> None:
        with self._lock:
            self._update(words)

    def train(self, sentences: list[list[Word]]) -> None:
        with self._lock:
            [self._update(words) for words in sentences]

    @DeprecationWarning
    def get_top_k_words(self, k: int) -> dict[str, int]:
        """
        Return the top k words from the rankings.
        """
        with self._lock:
            if not self._is_sorted:
                self.logger.error(
                    "Rankings not sorted before get_top_k call, this should never happen!"
                )

            return dict(list(self._counts.items())[:k])

    @DeprecationWarning
    def get_words_for_topk_range(self, k_a: int, k_b: int) -> dict[str, int]:
        """
        Return rankings slice from k_a to k_b.
        """
        # Make sure that k_a and k_b are within bounds and that k_a < k_b
        k_a = max(0, k_a)
        k_b = max(k_a + 1, k_b)

        with self._lock:
            if not self._is_sorted:
                self.logger.error(
                    "Rankings not sorted before get_top_k_range call, this should never happen!"
                )

            return dict(list(self._counts.items())[k_a:k_b])

    def heapify(self) -> None:
        """
        Sort the rankings by count in descending order for efficient retrieval of top-k.
        This is blocking and should be called after batch updates to the rankings, not on every update.
        """
        with self._lock:
            self._counts = defaultdict(int, sorted(self._counts.items(), key=lambda x: x[1], reverse=True))
            self._is_sorted = True