from collections import defaultdict

from numpy import float32
import numpy as np
from numpy.typing import NDArray
import whisperx

from config import WHISPERX_SAMPLERATE, AUDIO_SNIPPET_POST_BUFFER, AUDIO_SNIPPET_PRE_BUFFER

from scipy.signal import resample_poly
from math import gcd

from util.logger import Logger
from util.Result import Failure, Result, Success

class NoTranscriptionError(Exception):
    pass

class Transcribe:
    def __init__(
            self, 
            batch_size: int, 
            logger: Logger,
            samplerate: int = 44100,
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

    def transcribe(
        self,
        audio: NDArray[float32],
    ) -> Result[tuple[str, dict], NoTranscriptionError]:
        """Transcribe and align audio, transparently chunking long recordings."""
        chunk_size = self.sample_rate * 60

        if len(audio) <= chunk_size:
            return self._transcribe_chunk(audio)

        transcripts = []
        segments = []

        for start in range(0, len(audio), chunk_size):
            result = self._transcribe_chunk(audio[start:start + chunk_size])

            if result.is_failure():
                return result

            transcript, alignment = result.get_value()
            offset = start / self.sample_rate

            transcripts.append(transcript)
            for segment in alignment["segments"]:
                self._offset_timestamps(segment, offset)
                segments.append(segment)

        return Success((
            " ".join(transcripts),
            {"segments": segments},
        ))


    def _transcribe_chunk(
        self,
        audio: NDArray[float32],
    ) -> Result[tuple[str, dict], NoTranscriptionError]:
        """Transcribe and align a single audio chunk."""
        resampled_audio = self._resample(audio.copy())

        if resampled_audio.ndim == 2:
            resampled_audio = resampled_audio.squeeze(1)

        self.logger.debug(
            f"Audio shape: {audio.shape}, dtype: {audio.dtype}, "
            f"min: {audio.min():.3f}, max: {audio.max():.3f}"
        )
        self.logger.debug(
            f"Processing {len(audio) / self.sample_rate:.2f}s "
            f"({audio.nbytes / 1024 / 1024:.1f} MB)"
        )

        result = self.transcription_model.transcribe(
            resampled_audio,
            batch_size=self.batch_size,
            language=self.language,
            task="transcribe",
        )

        if not result["segments"]:
            self.logger.error("Couldn't transcribe audio")
            return Failure(NoTranscriptionError())

        transcript = " ".join(
            segment["text"].strip()
            for segment in result["segments"]
            if segment.get("text")
        )

        aligned = whisperx.align(
            result["segments"],
            self.alignment_model,
            self.metadata,
            resampled_audio,
            self.device,
            return_char_alignments=False,
        )

        del resampled_audio

        return Success((transcript, aligned))


    @staticmethod
    def _offset_timestamps(segment: dict, offset: float) -> None:
        """Convert chunk-relative timestamps to recording-relative timestamps."""
        for item in [segment, *segment.get("words", [])]:
            if item.get("start") is not None:
                item["start"] += offset
            if item.get("end") is not None:
                item["end"] += offset


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