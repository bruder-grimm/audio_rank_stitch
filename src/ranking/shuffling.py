import random

from numpy import float32
from numpy.typing import NDArray

from util.logger import Logger


class Shuffle:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
    
    def shuffle_top_k(
        self,
        words: dict[str, list[NDArray[float32]]],
        ranks: dict[str, int],
        shuffle_factor: float,
    ) -> list[NDArray[float32]]:
        """
        Create a weighted shuffled playback stream.

        shuffle_factor:
            0.0 -> only top word
            1.0 -> fully mixed/random
        """
        if not words:
            return []

        if len(words) == 1:
            return list(words[0][1])

        shuffle_factor = max(0.0, min(1.0, shuffle_factor))

        top_word, top_audio = words[0]
        other_words = words[1:]

        result: list[NDArray[float32]] = []
        debug_words: list[str] = []

        # Copy so we do not mutate original data
        remaining_top = list(top_audio)

        while remaining_top:
            use_other = random.random() < shuffle_factor

            if use_other and other_words:
                chosen_word, chosen_audio = random.choice(other_words)

                if chosen_audio:
                    result.append(random.choice(chosen_audio))
                    debug_words.append(chosen_word)
                    continue

            # Fallback/default = consume top word in order
            result.append(remaining_top.pop(0))
            debug_words.append(top_word)

        self.logger.debug(
            f"Generated playback sequence: {debug_words}"
        )

        return result
