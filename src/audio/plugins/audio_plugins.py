from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class AudioPlugin(Protocol):
    def process(self, audio: NDArray[np.float32]) -> NDArray[np.float32]:
        ...
