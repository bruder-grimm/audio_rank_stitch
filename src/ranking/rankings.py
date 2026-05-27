from collections import defaultdict
from pathlib import Path
import threading

from util.logger import Logger


class Rankings:
    """
    Our in memory ranking system.
    """

    def __init__(self, logger: Logger) -> None:
        self._counts: dict[str, int] = defaultdict(int)
        self._is_sorted = False
        self._lock = threading.Lock()

        self.logger = logger

    def build_rankings_from_disk(self, path: Path):
        """Load rankings from disk and populate the in-memory rankings."""
        if not path.exists() or not path.is_dir():
            return
        
        for word_dir in path.iterdir():
            if not word_dir.is_dir():
                continue
            
            for file in word_dir.iterdir():
                if file.is_file() and file.suffix.lower() == ".wav":
                    self._counts[word_dir.name] += 1


    def is_empty(self) -> bool:
        with self._lock:
            return len(self._counts) == 0

    def update_with(self, rankings: dict[str, int]) -> None:
        """Accumulate another rankings dict into this one."""
        with self._lock:
            for word, count in rankings.items():
                word = word.lower().strip()  # sanitize for my sanity
                self._counts[word] += count

            self._is_sorted = False

    def update_from(self, strings: list[str]) -> None:
        """Count incoming strings and merge them into the live rankings."""
        with self._lock:
            for string in strings:
                string = string.lower().strip()
                self._counts[string] += 1

            self._is_sorted = False

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
            self._counts = {
                k: v
                for k, v in sorted(
                    self._counts.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            }

            self._is_sorted = True