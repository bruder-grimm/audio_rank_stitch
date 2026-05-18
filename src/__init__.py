from numpy import float32, uint8
from numpy.typing import NDArray


type Wav = NDArray[float32]
type Sequence = NDArray[uint8]

# Timecode is supposed to be a samplerate adjusted step
type Step = int
type Timecode = int