from collections import defaultdict
from pathlib import Path
from time import time

import numpy as np
from numpy import int16, int16
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
        self.buffer: dict[Path, tuple[int, NDArray[int16]]]

    def load_waves_for(self, word: str) -> Result[list[NDArray[int16]], Exception]:
        """
        Returns all recordings of the requested words
        If the samplingrate doesn't match the one we're working with we've got a problem for sure
        """
        try:
            # Get ((samplerates, waves), filenames) from our word folder
            result: list[tuple[tuple[int, NDArray[int16]], str]] = [
                (self._buffered_read(wave_file), wave_file.name) 
                for wave_file in (self.path / word).iterdir()
                if wave_file.is_file()
            ]
            
            if len(result) == 0:
                self.logger.warn(f"Tried to access waves for word with no waves saved: {word}")
                raise NoRecordingsError(f"No waves saved for word: {word}")
            
            # We sort the list in descending order because we want the newest recordings to be playes first
            for ((sampling_rate, _), file_name) in sorted(result, reverse=True):
                if sampling_rate != self.sampling_rate:
                    self.logger.error(f"Encountered sample rate mismatch at {file_name}")
                    raise SamplingRateMismatch(f"{file_name} doesn't match given sampling rate of {sampling_rate}")
                
        except Exception as e:
            self.logger.error(f"Ecountered error while loading waves: {e}")
            return Failure(e)
        
        return Success([wave for ((_, wave), _) in result])
    
    def save_waves(self, words_with_audio: dict[str, list[NDArray[int16]]]) -> Result[int, Exception]:
        """
        Saves all wave forms to their corresponding folders.
        Will return the number of saved items on success, error on failure
        """
        try:
            for word, waves in words_with_audio.items():
                path = (self.path / word)
                path.mkdir(parents=True, exist_ok=True)

                for wave in waves:
                    self._buffered_write(path, self.sampling_rate, wave)

        except Exception as e:
            self.logger.error(f"Encountered error while saving waves: {e}")
            return Failure(e)
        
        return Success(len(words_with_audio))
    
    
    def _buffered_read(self, path: Path) -> tuple[int, NDArray[int16]]:
        if path not in self.buffer.keys():
            samplerate, audio = wavfile.read(path)
            self.buffer[path] = (samplerate, audio.astype(int16))
        
        return self.buffer[path]
    
    def _buffered_write(self, path: Path, sampling_rate: int, audio: NDArray[int16]) -> None:
        self.buffer[path] = (sampling_rate, audio)
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write((path / f"{time()}.wav"), self.sampling_rate, audio_int16)