import numpy as np
from numpy import float32
from numpy.typing import NDArray
import sounddevice as sd


class Player():
    def __init__(self, samplerate: int = 44100) -> None:
        self.samplerate = samplerate

    def play(self, wave: NDArray[float32], attack: float = 0.5, decay: float = 0.5) -> None:
        wave_1d = wave.flatten()
        total = len(wave_1d)

        n_attack = min(int(self.samplerate * attack), total // 2)
        n_decay = min(int(self.samplerate * decay), total // 2)

        env = np.ones(total)
        env[:n_attack] = np.linspace(0, 1, n_attack)
        env[-n_decay:] = np.linspace(1, 0, n_decay)

        sd.play((wave_1d * env).astype(np.float32), self.samplerate)
        sd.wait()
