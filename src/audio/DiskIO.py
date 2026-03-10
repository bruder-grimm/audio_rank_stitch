from pathlib import Path
from time import time

import numpy as np
from numpy import float32
from numpy.typing import NDArray

from scipy.io import wavfile

from util.Result import Failure, Result, Success
from scipy.io import wavfile

class NoRecordingsError(Exception):
    pass

class SamplingRateMismatch(Exception):
    pass


class DiskIO():
    def __init__(self, path: Path, sampling_rate: int = 44100) -> None:
        self.path = path
        self.sampling_rate = sampling_rate

    def load_waves_for(self, word: str) -> Result[list[NDArray[float32]], Exception]:
        """
        Returns all recordings of the requested words
        If the samplingrate doesn't match the one we're working with we've got a problem for sure
        """
        try:
            # Get ((samplerates, waves), filenames) from our word folder
            result: list[tuple[tuple[int, NDArray[float32]], str]] = [
                (wavfile.read(wave), wave.name) 
                for wave in (self.path / word).iterdir() 
                if wave.is_file()
            ]
            
            if len(result) == 0:
                raise NoRecordingsError(f"No waves saved for word: {word}")
            
            for ((sampling_rate, _), file_name) in result:
                if sampling_rate != self.sampling_rate:
                    raise SamplingRateMismatch(f"{file_name} doesn't match given sampling rate of {sampling_rate}")
                
        except Exception as e:
            return Failure(e)
        
        return Success([wave for ((_, wave), _) in result])
        
    
    def save_waves(self, waves: dict[str, NDArray[float32]]) -> Result[int, Exception]:
        """
        Saves all wave forms to their corresponding folders.
        Will return the number of saved items on success, error on failure
        """
        try:
            for word, wave in waves.items():
                path = (self.path / word)
                path.mkdir(parents=True, exist_ok=True)

                audio_int16 = (wave * 32767).astype(np.int16)
                wavfile.write(f"{time()}.wav", self.sampling_rate, audio_int16)
                
        except Exception as e:
            return Failure(e)
        
        return Success(len(waves))


