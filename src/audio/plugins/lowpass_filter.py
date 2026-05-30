import numpy as np
from scipy.signal import butter, sosfilt
from numpy.typing import NDArray


class LowPassFilter:
    def __init__(self, sample_rate: int, cutoff_hz: float = 8000.0, order: int = 4):
        self.sos = butter(
            order,
            cutoff_hz,
            btype="low",
            fs=sample_rate,
            output="sos",
        )

    def process(self, audio: NDArray[np.float32]) -> NDArray[np.float32]:
        filtered = sosfilt(self.sos, audio)
        return filtered.astype(np.float32) # type: ignore