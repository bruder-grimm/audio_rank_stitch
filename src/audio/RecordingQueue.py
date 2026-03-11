from typing import Optional

from numpy import int16
from numpy.typing import NDArray


class RecordingQueue():
    def __init__(self) -> None:
        self.queue = []

    def append(self, audio: NDArray[int16]):
        self.queue.append(audio)

    def get(self) -> Optional[NDArray[int16]]:
        try:
            self.queue.pop(0)
        except IndexError:
            return None