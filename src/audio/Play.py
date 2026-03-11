import numpy as np
from numpy import int16
from numpy.typing import NDArray
import sounddevice as sd


class Player():
    def __init__(self, samplerate: int = 44100) -> None:
        self.samplerate = samplerate

    def play(self, wave: NDArray[int16], attack: float = 0.5, decay: float = 0.5) -> None:
        """
        Does what it says on the tin my guy
        """
        n_attack = int(self.samplerate * attack)
        n_decay = int(self.samplerate * decay)

        env = np.ones(len(wave))
        env[:n_attack] = np.linspace(0, 1, n_attack)
        env[-n_decay:] = np.linspace(1, 0, n_decay)

        sd.play(wave * env, self.samplerate)
        sd.wait()
