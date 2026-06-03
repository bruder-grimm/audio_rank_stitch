from scipy.signal import butter, sosfilt, sosfilt_zi
import numpy as np
from numpy.typing import NDArray

class LowPassFilter:
    def __init__(self, sample_rate: float = 44100.0, cutoff_hz: float = 8000.0, order: int = 4):
        nyquist = sample_rate / 2.0
        self.sos = butter(order, cutoff_hz / nyquist, btype='low', output='sos')
        self.zi = sosfilt_zi(self.sos)

    def process(self, audio: NDArray[np.float32]) -> NDArray[np.float32]:
        filtered, self.zi = sosfilt(self.sos, audio, zi=self.zi)
        return filtered.astype(np.float32)