from collections import defaultdict

from numpy import float32
import numpy as np
from numpy.typing import NDArray
import whisperx

from config import WHISPERX_SAMPLERATE, AUDIO_SNIPPET_POST_BUFFER, AUDIO_SNIPPET_PRE_BUFFER

from scipy.signal import resample_poly
from math import gcd

from util.Logger import Logger
from util.Result import Failure, Result, Success

class NoTranscriptionError(Exception):
    pass

class Transcribe:
    def __init__(
            self, 
            batch_size: int, 
            logger: Logger,
            samplerate: int,
            device: str = "cpu", 
            language: str = "en"
        ):
        self.sample_rate = samplerate
        self.batch_size = batch_size
        self.device = device
        self.language = language
        self.logger = logger

        self.pre_buffer = int(AUDIO_SNIPPET_PRE_BUFFER * samplerate)
        self.post_buffer = int(AUDIO_SNIPPET_POST_BUFFER * samplerate)

        self.transcription_model = whisperx.load_model(
            "medium.en", device, compute_type="int8"
        )
        self.alignment_model, self.metadata = whisperx.load_align_model(
            language_code=language, device=self.device
        )

    def transcribe(self, audio: NDArray[float32]) -> Result[tuple[str, dict], NoTranscriptionError]:
        """
        Transcribe float32 numpy audio to text with alignment.
        Returns dict with 'text' and 'segments' (including word timestamps).
        """
        
        # Right, so this is a whole can of worms
        # 1. We convert, cast, and flatten, and then resample our audio data
        #   whisperx needs float32, and (time, ) as shape
        
        # audio_float32 = audio.astype(np.float32) / 32768.0
        resampled_audio = self._resample(audio.copy())

        if resampled_audio.ndim == 2:
            resampled_audio = resampled_audio.squeeze(1)  # (time, 1) -> (time,)
        
        self.logger.debug(f"Audio shape: {audio.shape}, dtype: {audio.dtype}, min: {audio.min():.3f}, max: {audio.max():.3f}")

        # 2. We transcribe with this new 1D array
        result = self.transcription_model.transcribe(
            resampled_audio,
            batch_size=self.batch_size,
            language=self.language,
            task="transcribe",
        )

        # Bonus: we fail
        if len(result["segments"]) == 0:
            self.logger.error("Coulnt' transcribe audio")
            return Failure(NoTranscriptionError())
        
        # ...unless 👀
        try:
            transcript = result["segments"][0]["text"]
            self.logger.debug(f"Successfully transcribed:\n {transcript}")
        except Exception as e:
            return Failure(NoTranscriptionError())

        # 3. We align
        result_aligned = whisperx.align(
            result["segments"],
            self.alignment_model,
            self.metadata,
            resampled_audio,
            self.device,
            return_char_alignments=False
        )

        self.logger.debug(f"Successfully aligned: \n {result_aligned['segments']}")
        del resampled_audio

        return Success((transcript, result_aligned))  # Return the full dict for access to timestamps

    def get_words_with_audio(
            self, 
            audio: NDArray[float32], 
            transcription: dict, 
        ) -> dict[str, list[NDArray[float32]]]:
        """
        Cuts the audio into segments based on word timestamps.
        Returns a list of (word, audio_segment) tuples.
        """
        words = defaultdict(list)
        self.logger.debug("Begin word slicing")

        for segment in transcription["segments"]:
            for word_info in segment["words"]:
                self.logger.debug(f"Processing {word_info}")

                start_sample = max(0, int(word_info["start"] * self.sample_rate) - self.pre_buffer)
                end_sample = min(len(audio), int(word_info["end"] * self.sample_rate) + self.post_buffer)

                word_audio = audio[start_sample:end_sample]
                words[word_info["word"]].append(word_audio)

        self.logger.debug(f"Slicing successful:\n {dict(words)}")
        
        return dict(words)
    
    def _resample(self, audio: NDArray[float32]) -> NDArray[float32]:
        divisor = gcd(self.sample_rate, WHISPERX_SAMPLERATE)
        up = WHISPERX_SAMPLERATE // divisor
        down = self.sample_rate // divisor
        return resample_poly(audio, up, down).astype(np.float32)