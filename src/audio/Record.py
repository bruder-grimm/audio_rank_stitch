from typing import Optional

from numpy.typing import NDArray
import sounddevice as sd
import numpy as np

from typing import Optional

from util.Logger import Logger
from util.Result import Result, Success, Failure
import sounddevice as sd
import numpy as np

class RecordingError(Exception):
    pass

class StreamClosedError(RecordingError):
    pass


class Recorder:
    def __init__(self, samplerate: int = 44100, channels: int = 1, logger: Optional[Logger] = None):
        self.samplerate = samplerate
        self.channels = channels
        self.frames: Optional[np.ndarray] = None
        self.stream: Optional[sd.InputStream] = None
        self.logger = logger

    def _callback(self, indata, frames, time, status):
        if self.logger:
            self.logger.info("Received audio data")
            #self.logger.debug(f"Indata shape: {indata.shape}, frames: {frames}, time: {time}, status: {status}")
        self.frames = indata.copy()

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
            dtype="int16",
            callback=self._callback,
        )
        self.stream.start()

    def stop(self) -> Result[NDArray[np.int16], RecordingError]:
        """
        Will stop the recording, return the successfully accumulated audio data
        Or an error in case anything went wrong
        """
        if self.stream is None:
            return Failure(StreamClosedError("Stream was not open"))
        if self.frames is None:
            return Failure(RecordingError("No data has been recorded"))
        
        try:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        except Exception as e:
            return Failure(RecordingError(f"Failed to stop stream: {e}"))

        result = np.concatenate(self.frames, axis=0)
        self.frames = None
        
        return Success(result)