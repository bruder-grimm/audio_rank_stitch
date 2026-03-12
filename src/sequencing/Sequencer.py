from numpy import float32, uint8
from numpy.typing import NDArray
import numpy as np

from util.Logger import Logger


class Sequencer():
    def __init__(
            self, 
            logger: Logger,
            sample_rate: int,
            kick_drum: NDArray[float32] = np.empty(0, dtype=float32),
            snare_drum: NDArray[float32] = np.empty(0, dtype=float32),
            high_hat: NDArray[float32] = np.empty(0, dtype=float32),
            toms: NDArray[float32] = np.empty(0, dtype=float32),
            cymbal: NDArray[float32] = np.empty(0, dtype=float32),
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
            # ---------------------------- PART PATTERN SELECTION LOGIC ---------------------------- #
            # This is still subject to scrutiny.
            # We want to be able to actually have some randomness/variance to the patterns
            # Not sure how we would handle this in the most user friendly way...
            if part == "kick_drum":
                pattern = self._get_kick_drum_pattern(number_of_steps)
            elif part == "snare_drum":
                pattern = self._get_snare_drum_pattern(number_of_steps)
            elif part == "high_hat":
                pattern = self._get_high_hat_pattern(number_of_steps)
            else:
                pattern = self._get_random_pattern(number_of_steps)

            self.logger.debug(f"{part}: {pattern}")
            for step, is_on in enumerate(pattern):
                if is_on:
                    result.append(((step * step_size), sound))

        return result

    # ----------------------------------- PATTERN GENERATION LOGIC ---------------------------------- #
    def _get_random_pattern(self, number_of_steps: int) -> NDArray[uint8]:
        K = int(number_of_steps / 2)
        grid: NDArray = np.array([0] * K + [1] * (number_of_steps-K))
        np.random.shuffle(grid)

        return grid
    
    def _get_kick_drum_pattern(self, number_of_steps: int) -> NDArray[uint8]:
        pattern = np.zeros(number_of_steps, dtype=uint8)
        pattern[0] = 1
        pattern[number_of_steps // 2] = 1

        return pattern
    
    def _get_snare_drum_pattern(self, number_of_steps: int) -> NDArray[uint8]:
        pattern = np.zeros(number_of_steps, dtype=uint8)
        pattern[number_of_steps // 4] = 1
        pattern[3 * number_of_steps // 4] = 1

        return pattern
    
    def _get_high_hat_pattern(self, number_of_steps: int) -> NDArray[uint8]:
        pattern = np.zeros(number_of_steps, dtype=uint8)
        pattern[::2] = 1

        return pattern
