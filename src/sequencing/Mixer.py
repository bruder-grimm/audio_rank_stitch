from numpy import float32
from numpy.typing import NDArray
import numpy as np


class Mixer():
    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    def mix_down(
            self, 
            sequence_length: int, 
            step_length: float, 
            parts_with_timing: list[tuple[int, NDArray[float32]]]
        ) -> NDArray[float32]:
        step_size = int(self.sample_rate * step_length)
        result = np.zeros(sequence_length * step_size, dtype=float32)

        for time, part in parts_with_timing:
            end = min((time + len(part), len(result)))
            result[time:end] += part[:end - time]

        peak = np.max(np.abs(result))
        if peak > 1.0:
            result /= peak
        
        return result


