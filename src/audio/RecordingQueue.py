from typing import Optional

from numpy import int16
from numpy.typing import NDArray

from util.Logger import Logger


class RecordingQueue():
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.queue: list[NDArray[int16]] = []

    def append(self, audio: NDArray[int16]):
        self.logger.debug(f"Added {len(audio)} audio frames to Queue")
        self.queue.append(audio)

    def get(self) -> Optional[NDArray[int16]]:
        try:
            element = self.queue.pop(0)
            self.logger.debug("Got first element from queue")
            
            return element
        except IndexError:
            self.logger.debug("Requested item from empty")
            return None