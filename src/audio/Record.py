from typing import Optional

import sounddevice as sd
import numpy as np

from typing import Optional

from audio.RecordingQueue import RecordingQueue
from util.Logger import Logger
import sounddevice as sd
import numpy as np

class RecordingError(Exception):
    pass

class StreamClosedError(RecordingError):
    pass


class Recorder:
    def __init__(
            self,
            recording_queue: RecordingQueue,
            logger: Logger,
            samplerate: int = 44100, 
            channels: int = 1, 
        ):
        self.samplerate = samplerate
        self.channels = channels
        self.recording_queue = recording_queue
        self.frames: list = []
        self.stream: Optional[sd.InputStream] = None
        self.logger = logger

    def _callback(self, indata, frames, time, status):
        self.frames.append(indata.copy())

    def start(self):
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

    def stop(self):
        """
        Will stop the recording, return the successfully accumulated audio data
        Or an error in case anything went wrong
        """
        if self.stream is None:
            self.logger.error("Stream was not open")
            return
        if self.frames is None:
            self.logger.error("No data has been recorded")
            return
        
        try:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        except Exception as e:
            self.logger.error(f"Failed to stop stream: {e}")
            return
        
        full_audio = np.concatenate(self.frames, axis=0)

        # Add some normalization to prevent clipping and ensure consistent volume levels
        target_rms = 0.1  # tune this, 0.1 is a good starting point for speech
        current_rms = np.sqrt(np.mean(full_audio ** 2))
        full_audio = full_audio * (target_rms / (current_rms + 1e-9))
        full_audio = np.clip(full_audio, -1.0, 1.0)  # prevent clipping

        self.recording_queue.append(full_audio)
        self.frames = []
