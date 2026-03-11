from collections import defaultdict

import numpy as np
from numpy import int16
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

    def transcribe(self, audio: NDArray[np.int16]) -> dict:
        """
        Transcribe int16 numpy audio to text with alignment.
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
        for segment in transcription["segments"]:
            for word_info in segment["words"]:
                start_sample = int(word_info["start"] * samplerate)
                end_sample = int(word_info["end"] * samplerate)
                word_audio = audio[start_sample:end_sample]
                words[word_info["word"]].append(word_audio)
        
        return dict(words)