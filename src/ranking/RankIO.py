from collections import defaultdict
import json
import math
import os
from pathlib import Path
from typing import Dict, Optional
from util.Result import Result, Success, Failure
from util.Logger import Logger

RANKINGS_FILE = "rankings.json"

class RankIOError(Exception):
    pass

class NoAudioFilesError(Exception):
    pass


class RankIO():
    def __init__(self, path: Path, logger: Logger) -> None:
        self.working_directory = path
        self.ranking_file = path / RANKINGS_FILE
        self.logger = logger
        self.buffer: Optional[dict[str, int]] = None

        self.last_modified: float = os.stat(path).st_mtime

    def save_rankings(self, rankings: dict[str, int]) -> Result[int, RankIOError]:
        """
        Creates or updates the rankings.json file with the provided rankings dictionary.
        Returns number of entries on success.
        """
        try:
            self.logger.debug(f"Trying to save rankings. WD is {self.working_directory.absolute}")
            return Success(self._buffered_write(rankings))
        
        except OSError:  # we're done here
            self.logger.error("OSError encountered during saving of ranks. The app will crash now!")
            raise
        except Exception as e:
            return Failure(RankIOError(e))
        
    def generate_rankings(self) -> Result[dict[str, int], NoAudioFilesError]:
        """
        Generates a rankings dictionary based on present word snippets.
        """
        result = defaultdict(int)
        self.logger.debug(f"Generating rankings from {self.working_directory}")
        for word_dir in self.working_directory.iterdir():
            if not word_dir.is_dir():
                continue

            self.logger.debug(f"Found word {word_dir}")
            for file in word_dir.iterdir():
                if not file.is_file():
                    continue

                word = word_dir.name.lower().strip()
                self.logger.debug(f"Add one to {word}")
                result[word] += 1

        if len(result) == 0:
            return Failure(NoAudioFilesError())

        return Success(dict(result))

    def load_rankings(self) -> Result[dict[str, int], RankIOError]:
        """
        Loads rankings from the rankings.json. Rankings are of {str: int}
        That is {"word": occurance}
        If the contents of the working directory has changes since the last fetch, this might take some more time
        If the file does not exist this will fail
        """
        try:
            self.logger.debug(f"Loading rankings from {self.ranking_file.absolute}")
            return Success(self._buffered_read())
        
        except FileNotFoundError:
            return Failure(RankIOError(f"Ranking file not found at {self.ranking_file.absolute}"))
        except Exception as e:
            return Failure(RankIOError(e))
        

    def _audio_files_have_changed(self) -> bool:
        potentially_new_last_modified = os.stat(self.working_directory).st_mtime
        if math.isclose(self.last_modified, potentially_new_last_modified, rel_tol=1e-9):
            return False
        
        self.last_modified = potentially_new_last_modified
        return True
        
    def _buffered_read(self) -> dict[str, int]:
        if not self.buffer:
            with open(self.ranking_file, "r", encoding="utf-8") as f:
                buffer = json.load(f)
                self.buffer = buffer
                return buffer
        else:
            return self.buffer
        
    def _buffered_write(self, rankings: dict[str, int]) -> int:
        self.ranking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ranking_file, "w", encoding="utf-8") as f:
            json.dump(rankings, f, indent=2)

        self.buffer = rankings
        return len(rankings)