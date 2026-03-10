from numpy import float32
from numpy.typing import NDArray
import sounddevice as sd
from audio.DiskIO import DiskIO


class Player():
    def __init__(self, disk_io: DiskIO, samplerate: int = 44100) -> None:
        self.samplerate = samplerate
        self.disk_io = disk_io

    def play(self, wave: NDArray[float32]):
        """
        Does what it says on the tin my guy
        """
        sd.play(wave, self.samplerate)
        sd.wait()
