import json
from pathlib import Path
from typing import Dict
from util.Result import Result, Success, Failure


class RankingsIOError(Exception):
    pass

class RankIO():
    def __init__(self, path: Path) -> None:
        self.path = path

    def save_rankings(self, rankings: dict[str, int]) -> Result[int, RankingsIOError]:
        """
        Creates or updates the rankings.json file with the provided rankings dictionary.
        Returns number of entries on success.
        """
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(rankings, f, indent=2)

            return Success(len(rankings))
        except Exception as e:
            return Failure(RankingsIOError(e))


    def load_rankings(self) -> Result[dict[str, int], RankingsIOError]:
        try:
            if not self.path.exists():
                return Success({})

            with open(self.path, "r", encoding="utf-8") as f:
                data: Dict[str, int] = json.load(f)

            return Success(data)
        except Exception as e:
            return Failure(RankingsIOError(e))