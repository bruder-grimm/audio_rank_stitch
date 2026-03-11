from collections import defaultdict

from numpy import int16
import numpy as np
from numpy.typing import NDArray
import torch
import whisperx

from util.Logger import Logger
from util.Result import Failure, Result, Success

class NoTranscriptionError(Exception):
    pass

class Transcribe:
    def __init__(
            self, 
            batch_size: int, 
            logger: Logger,
            device: str = "cpu", 
            language: str = "en"
        ):
        self.batch_size = batch_size
        self.device = device
        self.language = language
        self.logger = logger

        self.transcription_model = whisperx.load_model(
            "medium.en", device, compute_type="int8"
        )
        self.alignment_model, self.metadata = whisperx.load_align_model(
            language_code=language, device=self.device
        )

    def transcribe(self, audio: NDArray[int16]) -> Result[dict, NoTranscriptionError]:
        """
        Transcribe int16 numpy audio to text with alignment.
        Returns dict with 'text' and 'segments' (including word timestamps).
        """
        audio_float32 = audio.astype(np.float32) / 32768.0
        # Right, so this is a whole can of worms
        # Flatten to 1D for mono
        if audio_float32.ndim == 2:
            audio_float32 = audio_float32.squeeze(1)  # (time, 1) -> (time,)

        # 1. Transcribe with 1D array
        result = self.transcription_model.transcribe(
            audio_float32,
            batch_size=self.batch_size,
            language=self.language,
            task="translate"
        )

        if len(result["segments"]) == 0:
            self.logger.error("Coulnt' transcribe audio")
            return Failure(NoTranscriptionError())
        
        self.logger.debug(f"Successfully transcribed:\n {result["segments"]}")

        # 2. Convert for alignment — pass flat float32 numpy array, NOT a tensor
        # whisperx.align expects shape (time,) for mono or handles it internally
        audio_for_align = audio_float32  # shape: (time,) or (time, 1)
        if audio_for_align.ndim == 2 and audio_for_align.shape[1] == 1:
            audio_for_align = audio_for_align.squeeze(1)  # (time,)

        # 3. Align
        result_aligned = whisperx.align(
            result["segments"],
            self.alignment_model,
            self.metadata,
            audio_for_align,
            self.device,
            return_char_alignments=False
        )

        self.logger.debug(f"Successfully aligned: \n {result["segments"]}")

        return Success(result_aligned)  # Return the full dict for access to timestamps

    def get_words_with_audio(
            self, 
            audio: NDArray[int16], 
            transcription: dict, 
            samplerate: int = 44100
        ) -> dict[str, list[NDArray[int16]]]:
        """
        Cuts the audio into segments based on word timestamps.
        Returns a list of (word, audio_segment) tuples.
        """
        words = defaultdict(list)
        self.logger.debug("Begin word slicing")
        for segment in transcription["segments"]:
            for word_info in segment["words"]:
                self.logger.debug(f"Processing {word_info}")
                start_sample = int(word_info["start"] * samplerate)
                end_sample = int(word_info["end"] * samplerate)
                word_audio = audio[start_sample:end_sample]
                words[word_info["word"]].append(word_audio)

        self.logger.debug(f"Slicing successful:\n {dict(words)}")
        
        return dict(words)