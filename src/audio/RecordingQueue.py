from typing import Optional

from numpy import float32
from numpy.typing import NDArray

from util.Logger import Logger


class RecordingQueue():
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.queue: list[NDArray[float32]] = []

    def append(self, audio: NDArray[float32]):
        self.logger.debug(f"Added {len(audio)} audio frames to Queue")
        self.queue.append(audio)

    def get(self) -> Optional[NDArray[float32]]:
        try:
            element = self.queue.pop(0)
            self.logger.debug("Got first element from queue")
            
            return element
        except IndexError:
            self.logger.debug("Requested item from empty")
            return None