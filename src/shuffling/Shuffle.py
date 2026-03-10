import random

import numpy as np
from numpy import float32
from numpy.typing import NDArray

from util.logger import Logger


class Shuffle:
    def __init__(self, waves: dict[str, list[NDArray[float32]]], ranks: dict[str, int], logger: Logger) -> None:
        self.waves = waves
        self.ranks = ranks
        self.words = ranks.keys()
        self.logger = logger

    def get_top_k(self, k: int) -> list[tuple[str, list[NDArray[float32]]]]:
        top_words = [
            word for word, _ 
            in sorted(self.ranks.items(), key=lambda kv: kv[1], reverse=True)[:k]
        ]

        return [(top_word, self.waves[top_word]) for top_word in top_words]
    
    def shuffle_top_k(
            self, 
            words: list[tuple[str, list[NDArray[float32]]]], 
            shuffle_factor: float
        ) -> list[NDArray[float32]]:
        """
        Reshuffle the list for to a playable format. Will sample away from the top
        items with probability shuffle_factor!
        """
        top_word, top_audio = words.pop(0)
        self.logger.info(f"Shuffling words around {top_word}")

        probability = min(max(shuffle_factor, 0), 1)

        result = []
        result_string = []

        while True:
            if len(top_audio) == 0:
                break
            if random.random() < probability:
                chosen, spoken = random.choice(words)
                result_string.append(chosen)
                result.append(random.choice(spoken))
            else: 
                result_string.append(top_word)
                result.append(top_audio.pop(0))

        self.logger.debug(f"Random sampled the word string: {result_string}")
        return result
