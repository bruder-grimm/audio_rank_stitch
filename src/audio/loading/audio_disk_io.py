from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict

from audio.loading.filename import get_key_from_word
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile
import pyloudnorm as pyln

from util.logger import Logger
from util.result import Failure, Result, Success

class NoRecordingsError(Exception):
    pass


class SamplingRateMismatch(Exception):
    pass


@dataclass(frozen=True)
class Recording:
    sampling_rate: int
    timestamp: int
    wav: NDArray[np.float32]
    path: Path

    @property
    def file_name(self) -> str:
        return self.path.name


class DiskIO:
    def __init__(
        self,
        path: Path,
        logger: Logger,
        sampling_rate: int = 44100,
    ) -> None:
        self.path = path
        self.sampling_rate = sampling_rate
        self.logger = logger
        self.buffer: DefaultDict[str, list[Recording]] = defaultdict(list)
        self.meter = pyln.Meter(sampling_rate) # create BS.1770 meter

    def build_buffer_from_disk(self) -> None:
        """Populate the in-memory cache for all saved word recordings."""
        for word_dir in self.path.iterdir():
            if not word_dir.is_dir():
                continue

            word_key = get_key_from_word(word_dir.name)
            self._buffered_read_word(word_key)

        self.logger.debug(f"DiskIO buffer built with recordings for {len(self.buffer)} words")

    def get_latest_raw_recording(self) -> Result[NDArray[np.float32], Exception]:
        try:
            raw_files = [
                f for f in self.path.iterdir()
                if f.is_file()
                and f.suffix.lower() == ".wav"
                and f.name.startswith("raw_")
            ]

            if not raw_files:
                return Failure(NoRecordingsError("No raw recordings found"))
            
            latest_file = max(
                raw_files,
                key=lambda f: int(f.stem.removeprefix("raw_"))
            )

            samplerate, audio = wavfile.read(latest_file)

            if samplerate != self.sampling_rate:
                return Failure(SamplingRateMismatch(f"Expected {self.sampling_rate}, got {samplerate}")
            )
            return Success(np.asarray(audio, dtype=np.float32))

        except Exception as exc:
            return Failure(exc)


    def load_waves_for(self, word: str) -> Result[list[NDArray[np.float32]], Exception]:
        """Load recordings for a single word, newest first."""
        try:
            word_key = get_key_from_word(word)

            if word_key not in self.buffer:
                self.logger.warn(f"Cache miss for word: {word_key}")
                self._buffered_read_word(word_key)

            recordings = self.buffer.get(word_key, [])
            if not recordings:
                raise NoRecordingsError(f"No recordings found for word: {word_key}")

            recordings = sorted(recordings, key=lambda rec: rec.timestamp, reverse=True)
            waves: list[NDArray[np.float32]] = []

            for recording in recordings:
                if recording.sampling_rate != self.sampling_rate:
                    self.logger.error(
                        f"Encountered sample rate mismatch at {recording.file_name}: "
                        f"expected {self.sampling_rate} but got {recording.sampling_rate}"
                    )
                    raise SamplingRateMismatch(
                        f"{recording.file_name} does not match sampling rate {self.sampling_rate}"
                    )

                waves.append(recording.wav)

            return Success(waves)

        except Exception as exc:
            self.logger.error(f"Encountered error while loading waves: {exc}")
            return Failure(exc)

    def save_waves_for(self, word: str, waves: list[NDArray[np.float32]]) -> Result[int, Exception]:
        """Save a list of waveforms for a single word."""
        try:
            word_key = get_key_from_word(word)
            word_dir = self.path / word_key
            word_dir.mkdir(parents=True, exist_ok=True)

            saved_count = 0

            for index, wave in enumerate(waves):
                file_path = word_dir / f"{int(time.time_ns())}_{index}.wav"
                self.logger.debug(f"Saving wav at {file_path}")
                self._buffered_write(word_key, file_path, wave)
                saved_count = index + 1

            return Success(saved_count)

        except Exception as exc:
            self.logger.error(f"Encountered error while saving waves: {exc}")
            return Failure(exc)

    def save_wave(self, audio: NDArray[np.float32]) -> Result[int, Exception]:
        """Save a single waveform to disk in a background thread without blocking."""
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            file_path = self.path / f"raw_{time.time_ns()}.wav"
            self.logger.debug(f"Scheduling async save for {file_path}")
            wavfile.write(file_path, self.sampling_rate, audio)
            return Success(1)
        except Exception as exc:
            self.logger.error(f"Encountered error while scheduling async save: {exc}")
            return Failure(exc)
        
    def save_transcription(self, transcription: str) -> Result[int, Exception]:
        """Save the transcription of a recording to disk."""
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            file_path = self.path / f"transcription_{time.time_ns()}.txt"
            self.logger.debug(f"Saving transcription at {file_path}")
            with open(file_path, "w") as f:
                f.write(transcription)
            return Success(1)
        except Exception as exc:
            self.logger.error(f"Encountered error while saving transcription: {exc}")
            return Failure(exc)
        
    def get_all_transcriptions(self) -> Result[list[str], Exception]:
        """Load all transcriptions from disk, oldest first."""
        try:
            if not self.path.exists() or not self.path.is_dir():
                return Failure(
                    FileNotFoundError(f"Transcript path does not exist: {self.path}")
                )

            files = sorted(
                (
                    file
                    for file in self.path.iterdir()
                    if file.is_file()
                    and file.suffix == ".txt"
                    and file.name.startswith("transcription_")
                ),
                key=lambda f: int(f.stem.removeprefix("transcription_")),
            )

            transcriptions = []
            for file in files:
                with open(file, "r") as f:
                    sentence = get_key_from_word(f.read()).lower()
                    transcriptions.append(sentence)

            return Success(transcriptions)

        except Exception as exc:
            self.logger.error(f"Encountered error while loading transcriptions: {exc}")
            return Failure(exc)

    def save_waves(self, words_with_audio: dict[str, list[NDArray[np.float32]]]) -> Result[int, Exception]:
        """Save multiple words and return the total number of saved files."""
        try:
            total = 0
            for word, waves in words_with_audio.items():
                result = self.save_waves_for(word, waves)
                if result.is_failure():
                    return result
                total += result.get_value()
            return Success(total)

        except Exception as exc:
            self.logger.error(f"Encountered error while saving multiple words: {exc}")
            return Failure(exc)

    def _buffered_read_word(self, word: str) -> None:
        self.buffer[word] = []
        word_dir = self.path / word

        if not word_dir.exists() or not word_dir.is_dir():
            return

        for wave_file in sorted(word_dir.iterdir()):
            if not wave_file.is_file() or wave_file.suffix.lower() != ".wav":
                continue

            recording = self._load_recording_from_file(wave_file)
            self.buffer[word].append(recording)

    def _load_recording_from_file(self, path: Path) -> Recording:
        samplerate, audio = wavfile.read(path)
        audio_array = np.asarray(audio, dtype=np.float32)
        timestamp = int(path.stem.split("_")[0])

        return Recording(
            sampling_rate=samplerate,
            timestamp=timestamp,
            wav=audio_array,
            path=path,
        )

    def _buffered_write(self, word: str, path: Path, audio: NDArray[np.float32]) -> None:
        timestamp = int(path.stem.split("_")[0])
        audio_copy = np.asarray(audio, dtype=np.float32).copy()
        
        # For normalization: measure the loudness first 
        loudness = self.meter.integrated_loudness(audio_copy)

        # loudness normalize audio to -12 dB LUFS
        loudness_normalized_audio = pyln.normalize.loudness(audio_copy, loudness, -12.0)

        self.buffer[word].append(
            Recording(
                sampling_rate=self.sampling_rate,
                timestamp=timestamp,
                wav=loudness_normalized_audio,
                path=path,
            )
        )
        wavfile.write(path, self.sampling_rate, loudness_normalized_audio)
