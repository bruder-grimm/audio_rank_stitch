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
        n_attack = min(int(self.samplerate * attack), total)
        n_decay = min(int(self.samplerate * decay), total)

        if n_attack + n_decay > total:
            scale = total / (n_attack + n_decay)
            n_attack = int(n_attack * scale)
            n_decay = int(n_decay * scale)

        env = np.ones(total)
        if n_attack > 0:
            env[:n_attack] = np.linspace(0, 1, n_attack)
        if n_decay > 0:
            env[-n_decay:] = np.linspace(1, 0, n_decay)

        sd.play((wave_1d * env).astype(np.float32), self.samplerate)
        sd.wait()
