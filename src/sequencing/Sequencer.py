from numpy import bool_, float32
from numpy.typing import NDArray
import numpy as np

from util.Logger import Logger


class Sequencer():
    def __init__(
            self, 
            kick_drum: NDArray[float32],
            snare_drum: NDArray[float32],
            high_hat: NDArray[float32],
            toms: NDArray[float32],
            cymbal: NDArray[float32],
            logger: Logger,
            sample_rate: int = 44100,
    ) -> None:
        self.parts = {
            "kick_drum": kick_drum,
            "snare_drum": snare_drum,
            "high_hat": high_hat,
            "toms": toms,
            "cymbal": cymbal,
        }
        self.sample_rate = sample_rate
        self.logger = logger

    def generate_sequence(
            self, 
            number_of_steps: int, 
            step_length: float
        ) -> list[tuple[int, NDArray[float32]]]:
        """
        Generates a pattern, probably randomly. Will have to be mixed down to be played by sounddevice
        """
        step_size = int(self.sample_rate * step_length)

        result = []
        for part, sound in self.parts.items():
            pattern = self._get_pattern(number_of_steps)
            self.logger.debug(f"{part}: {pattern}")
            for step, is_on in enumerate(pattern):
                if is_on:
                    result.append(((step * step_size), sound))

        return result


    def _get_pattern(self, number_of_steps: int) -> NDArray[bool_]:
        N = number_of_steps
        K = int(number_of_steps / 2)
        grid: NDArray = np.array([0] * K + [1] * (N-K))
        np.random.shuffle(grid)

        return grid.astype(bool)
