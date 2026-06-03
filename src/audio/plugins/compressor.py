from audiocomplib import AudioCompressor

import numpy as np
from numpy.typing import NDArray

class Compressor:
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        # Initialize compressor
        self.compressor = AudioCompressor(
            threshold=-10.0,
            ratio=4.0,
            attack_time_ms=1.0,
            release_time_ms=100.0,
            knee_width=3.0,
            variable_release=True,
            realtime=True
        )

    def process(self, audio: NDArray[np.float32]) -> NDArray[np.float32]:
        result = self.compressor.process(audio[np.newaxis, :], self.sample_rate)  # (frames,) → (1, frames)
        return result[0].astype(np.float32)