import numpy as np
from numpy.typing import NDArray
import whisperx


class Transcribe:
    def __init__(self, batch_size: int, data_type: str, device: str = "cpu", language: str = "en"):
        self.batch_size = batch_size
        self.data_type = data_type
        self.device = device
        self.language = language

        self.transcription_model = whisperx.load_model(
            "medium.en", device, compute_type=data_type
        )
        self.alignment_model, self.metadata = whisperx.load_align_model(
            language_code=language, device=self.device
        )

    def _transcribe(self, audio: NDArray[np.float32]) -> dict:
        """
        Transcribe float32 numpy audio to text with alignment.
        Returns dict with 'text' and 'segments' (including word timestamps).
        """
        result = self.transcription_model.transcribe(
            audio,
            batch_size=self.batch_size,
            language=self.language,
            task="translate"
        )

        result = whisperx.align(
            result["segments"], self.alignment_model, self.metadata, audio, self.device,
            return_char_alignments=False
        )

        return result  # Return the full dict for access to timestamps

    def get_words_with_audio(self, audio: NDArray[np.float32], samplerate: int = 44100) -> list:
        """
        Cuts the audio into segments based on word timestamps.
        Returns a list of (word, audio_segment) tuples.
        """
        result = self._transcribe(audio)
        words = []
        for segment in result["segments"]:
            for word_info in segment["words"]:
                start_sample = int(word_info["start"] * samplerate)
                end_sample = int(word_info["end"] * samplerate)
                word_audio = audio[start_sample:end_sample]
                words.append((word_info["word"], word_audio))
        
        return words