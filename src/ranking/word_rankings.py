from collections import defaultdict
from pathlib import Path
import json
from typing import Optional

from util.Result import Result, Success, Failure


class RankIOError(Exception):
    pass


class Rankings:
    """
    Our in memory ranking system.

    Owns all ranking data during runtime and can persist itself to disk when requested.
    """

    def __init__(self, initial: Optional[dict[str, int]] = None) -> None:
        self._counts: dict[str, int] = defaultdict(int)

        if initial:
            self._counts.update(initial)

    def update_with(self, rankings: dict[str, int]) -> None:
        """Accumulate another rankings dict into this one. """
        for word, count in rankings.items():
            word = word.lower().strip()  # sanitize for my sanity
            self._counts[word] += count

    def update_from_(self, strings: list[str]) -> None:
        """Count incoming strings and merge them into the live rankings."""
        for string in strings:
            string = string.lower().strip()
            self._counts[string] += 1

    def top_k(self, k: int) -> list[tuple[str, int]]:
        """
        Return the top k words from the rankings.
        """

        return sorted(
            self._counts.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )[:k]

    def persist(self, path: Path) -> Result[int, RankIOError]:
        """
        Persist current rankings state to disk.
        Returns number of entries written on success.
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(dict(self._counts), f, indent=2)
            return Success(len(self._counts))
        except OSError:
            # we're done here
            raise

        except Exception as e:
            return Failure(RankIOError(e))

    @classmethod
    def load(cls, path: Path) -> Result["Rankings", RankIOError]:
        """
        Load rankings from disk.
        If the file does not exist this will fail.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return Success(cls(data))

        except FileNotFoundError:
            return Failure(
                RankIOError(
                    f"Ranking file not found at {path.absolute()}"
                )
            )

        except Exception as e:
            return Failure(RankIOError(e))