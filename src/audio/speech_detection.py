import numpy as np
from numpy.typing import NDArray
import torch
from scipy.signal import resample_poly
from silero_vad import load_silero_vad, get_speech_timestamps

from util.Result import Result, Success, Failure

class NoSpeechDetectedError(Exception):
    pass

class SpeechDetector:
    def __init__(self, samplerate: int):
        self.sampling_rate = samplerate
        self.vad_sampling_rate = 16000
        self.vad_model = load_silero_vad()

    def contains_speech(self, audio: NDArray[np.float32]) -> Result[NDArray[np.float32], Exception]:
        to_check = np.asarray(audio.copy(), dtype=np.float32)

        # Convert to mono
        if to_check.ndim > 1:
            to_check = to_check.mean(axis=1)

        # clip to -1/1
        max_amplitude = np.max(np.abs(to_check))
        if max_amplitude > 1.0:
            to_check /= 32768.0

        # Silerowants 8 kHz or 16 kHz (and multiples of 16 kHz?)
        # So we just resample to 16 kHz.
        if self.sampling_rate != self.vad_sampling_rate:
            to_check = resample_poly(
                to_check,
                self.vad_sampling_rate,
                self.sampling_rate,
            ).astype(np.float32)

        speech_timestamps = get_speech_timestamps(
            torch.from_numpy(to_check),
            self.vad_model,
            sampling_rate=self.vad_sampling_rate,
            return_seconds=True,
        )
        del to_check

        if len(speech_timestamps) > 0:
            return Success(audio)

        else:
            return Failure(NoSpeechDetectedError("No words in recording"))
