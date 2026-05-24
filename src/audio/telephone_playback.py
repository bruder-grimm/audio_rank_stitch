from audio.mixer.audio_mixer import Mixer
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile

class TelephonePlayer:

    def __init__(self, mixer: Mixer, samplerate: int):
        self._mixer = mixer
        self.samplerate = samplerate
        self._recording_tone = np.asarray(
            wavfile.read("../../assets/recording_tone.wav")[1], dtype=np.float32
        ).flatten()
        self._start_dialing_tone = np.asarray(
            wavfile.read("../../assets/dialing_tone.wav")[1], dtype=np.float32
        ).flatten()


    def play(self, audio: NDArray[np.float32]) -> None:
        wave_1d = audio.flatten()
        self._mixer.queue_phone(wave_1d)

    def recording_start_beep(self) -> None:
        self._mixer.queue_phone(self._recording_tone)

    def dialing_start_beep(self) -> None:
        self._mixer.queue_phone(self._start_dialing_tone)
