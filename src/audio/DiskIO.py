from pathlib import Path
from time import time
import re

from numpy import float32, float32
from numpy.typing import NDArray

from scipy.io import wavfile

from util.Result import Failure, Result, Success
from scipy.io import wavfile

from util.Logger import Logger

class NoRecordingsError(Exception):
    pass

class SamplingRateMismatch(Exception):
    pass


class DiskIO():
    def __init__(self, path: Path, logger: Logger, sampling_rate: int = 44100) -> None:
        self.path = path
        self.sampling_rate = sampling_rate
        self.logger = logger

        # Since we don't want to endlessly block on IO in what is, for all intents and
        # purposes, a hot path, we're going to reference our already loaded wavs 
        # until we eventually run out of memory lol
        self.buffer: dict[Path, tuple[int, NDArray[float32]]] = {}

    def load_waves_for(self, word: str) -> Result[list[NDArray[float32]], Exception]:
        """
        Returns all recordings of the requested words
        If the samplingrate doesn't match the one we're working with we've got a problem for sure
        """
        try:
            # Get ((samplerates, waves), filenames) from our word folder
            result: list[tuple[tuple[int, NDArray[float32]], str]] = [
                (self._buffered_read(wave_file), wave_file.name) 
                for wave_file in (self.path / word).iterdir()
                if wave_file.is_file()
            ]
            
            if len(result) == 0:
                self.logger.warn(f"Tried to access waves for word with no waves saved: {word}")
                raise NoRecordingsError(f"No waves saved for word: {word}")
            
            # We sort the list in descending order because we want the newest recordings to be played first
            for ((sampling_rate, _), file_name) in sorted(result, key=lambda _: _[1], reverse=True):
                if sampling_rate != self.sampling_rate:
                    self.logger.error(f"Encountered sample rate mismatch at {file_name}")
                    raise SamplingRateMismatch(f"{file_name} doesn't match given sampling rate of {sampling_rate}")
                
        except Exception as e:
            self.logger.error(f"Ecountered error while loading waves: {e}")
            return Failure(e)
        
        return Success([wave for ((_, wave), _) in result])
    
    def save_waves(self, words_with_audio: dict[str, list[NDArray[float32]]]) -> Result[int, Exception]:
        """
        Saves all wave forms to their corresponding folders.
        Will return the number of saved items on success, error on failure
        """
        try:
            for word, waves in words_with_audio.items():
                path = (self.path / self._sanitize_filename(word))
                path.mkdir(parents=True, exist_ok=True)

                for i, wave in enumerate(waves):
                    self.logger.debug(f"saving wav at {path}")
                    self._buffered_write(path, self.sampling_rate, wave, i)

        except Exception as e:
            self.logger.error(f"Encountered error while saving waves: {e}")
            return Failure(e)
        
        return Success(len(words_with_audio))
    

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[<>:".,\'/\\|?*\x00-\x1f]', '', name).strip().lower()
    
    def _buffered_read(self, path: Path) -> tuple[int, NDArray[float32]]:
        if path not in self.buffer.keys():
            samplerate, audio = wavfile.read(path)
            self.buffer[path] = (samplerate, audio.astype(float32))
        
        return self.buffer[path]
    
    def _buffered_write(self, path: Path, sampling_rate: int, audio: NDArray[float32], occurance: int) -> None:
        self.buffer[path] = (sampling_rate, audio)
        wavfile.write((path / f"{int(time()) + occurance}.wav"), self.sampling_rate, audio)