import threading
from typing import Optional

from audio.mixer.audio_mixer import Mixer
import numpy as np
from numpy import float32
from numpy.typing import NDArray


class SpeakerPlayer():
    def __init__(self, mixer: Mixer, samplerate: int = 44100) -> None:
        self._mixer = mixer
        self.samplerate = samplerate

    def stop(self) -> None:
        self._mixer.stop_speaker()

    def play_blocking(
            self, 
            audio: NDArray[float32], 
            attack: float = 0.5, 
            decay: float = 0.5, 
            pre_trim: float = 0.0, 
            post_trim: float = 0.0
        ) -> None:
        """Play the given audio through the speaker, blocking until finished."""
        finished_event = threading.Event()
        self.play_async(audio, attack, decay, pre_trim, post_trim, finished_event)
        finished_event.wait()

    def play_async(
            self, 
            audio: NDArray[float32], 
            attack: float = 0.5, 
            decay: float = 0.5, 
            pre_trim: float = 0.0, 
            post_trim: float = 0.0,
            playback_finished_event: Optional[threading.Event] = None
        ) -> None:
        """
        Play the given audio through the speaker.
        Parameters:
        - audio: A 1D or 2D numpy array of float32 audio samples
        - attack: Time in seconds for the attack phase (fade-in)
        - decay: Time in seconds for the decay phase (fade-out)
        - pre_trim: Time in seconds to trim from the start of the audio
        - post_trim: Time in seconds to trim from the end of the audio
        - playback_finished_event: An optional threading.Event to signal when playback is finished
        """
        # TODO: Make sure this works!!!
        audio = np.mean(audio, axis=1) if audio.ndim > 1 else audio

        # Apply pre and post trimming
        start_idx = int(self.samplerate * pre_trim)
        end_idx = len(audio) - int(self.samplerate * post_trim)
        audio = audio[start_idx:end_idx]
        total = len(audio)

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

        self._mixer.queue_speaker((audio * env).astype(np.float32), playback_finished_event)

    def queue_silence(self, duration_seconds: float, playback_finished_event: Optional[threading.Event] = None) -> None:
        """Queue a silence of the given duration after the audio that is in the buffer atm"""
        num_samples = int(self.samplerate * duration_seconds)
        silence = np.zeros(num_samples, dtype=np.float32)
        self._mixer.queue_speaker(silence, playback_finished_event)