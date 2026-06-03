from typing import Optional

from numpy.typing import NDArray
import sounddevice as sd
import numpy as np

from typing import Optional

from util.logger import Logger
import sounddevice as sd
import numpy as np
from util.result import Failure, Result, Success

class RecordingError(Exception):
    pass

class StreamClosedError(RecordingError):
    pass


class Recorder:
    def __init__(
            self,
            logger: Logger,
            samplerate: int = 44100, 
            channels: int = 1, 
        ):
        self.samplerate = samplerate
        self.channels = channels
        self.frames: list = []
        self.stream: Optional[sd.InputStream] = None
        self.logger = logger

    def _callback(self, indata, frames, time, status):
        self.frames.append(indata.copy())

    def start_recording(self):
        """
        Starts the recording. There's probably some theoretical limit to how long this
        can run, and the app will most likely just crash if it's going for to long.
        But maybe we can handle this in the UI? There's a timer there, shouldn't
        be too big of a deal
        """
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            blocksize=256,
            callback=self._callback,
        )
        self.stream.start()

    def stop_and_get_recording(self) -> Result[NDArray[np.float32], Exception]:
        """
        Will stop the recording, return the successfully accumulated audio data
        Or an error in case anything went wrong
        """
        if self.stream is None:
            self.logger.error("Stream was not open")
            return Failure(StreamClosedError("Stream was not open"))
        if self.frames is None:
            self.logger.error("No data has been recorded")
            return Failure(RecordingError("No data has been recorded"))
        
        try:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        except Exception as e:
            self.logger.error(f"Failed to stop stream: {e}")
            return Failure(RecordingError(f"Failed to stop stream: {e}"))
        
        full_audio = np.concatenate(self.frames, axis=0)
        self.frames = []  # Clear frames for next recording

        return Success(self._normalize_audio(full_audio))


    def _normalize_audio(self, audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
        """Peak-safe RMS normalization.

        Scale the waveform so that its RMS is near `target_rms`, but never
        scale so high that the signal clips.
        """
        audio = np.asarray(audio, dtype=np.float32)
        current_rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))

        if current_rms < 1e-9 or peak < 1e-9:
            return audio

        gain = target_rms / current_rms
        peak_safe_gain = 1.0 / peak
        gain = min(gain, peak_safe_gain)

        normalized = audio * gain
        return np.clip(normalized, -1.0, 1.0)
