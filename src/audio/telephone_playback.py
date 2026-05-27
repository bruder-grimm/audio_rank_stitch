from threading import Event
from typing import Optional

from audio.mixer.audio_mixer import Mixer
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile

class TelephonePlayer:

    def __init__(self, mixer: Mixer, samplerate: int):
        self._mixer = mixer
        self.samplerate = samplerate
        self._recording_tone = np.mean(np.asarray(
            wavfile.read("../../assets/recording_tone.wav")[1], dtype=np.float32
        ), axis=1)
        self._start_dialing_tone = np.mean(np.asarray(
            wavfile.read("../../assets/dialing_tone.wav")[1], dtype=np.float32
        ), axis=1)

    def clear_queue(self):
        self._mixer.stop_phone()

    def play_silence_async(self, duration_seconds: float, playback_finished: Optional[Event] = None) -> None:
        num_samples = int(self.samplerate * duration_seconds)
        silence = np.zeros(num_samples, dtype=np.float32)
        self._mixer.queue_phone(silence, playback_finished)

    def play_async(self, audio: NDArray[np.float32], playback_finished: Optional[Event] = None) -> None:
        audio = np.mean(audio, axis=1) if audio.ndim > 1 else audio
        self._mixer.queue_phone(audio.astype(np.float32), playback_finished)

    def play_recording_start_beep_async(self, playback_finished: Optional[Event] = None) -> None:
        self._mixer.queue_phone(self._recording_tone, playback_finished)

    def play_dialing_start_beep_async(self, playback_finished: Optional[Event] = None) -> None:
        self._mixer.queue_phone(self._start_dialing_tone, playback_finished)

    def play_dialing_start_beep(self) -> None:
        self._mixer.play_phone_blocking(self._start_dialing_tone)

    def play_recording_start_beep(self) -> None:
        self._mixer.play_phone_blocking(self._recording_tone)
