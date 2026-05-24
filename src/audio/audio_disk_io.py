from __future__ import annotations

import re
import time
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Optional, TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile

from util.logger import Logger
from util.result import Failure, Result, Success

if TYPE_CHECKING:
    from app_state import AppState


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
        app_state: Optional[AppState] = None,
    ) -> None:
        self.path = path
        self.sampling_rate = sampling_rate
        self.logger = logger
        self.buffer: DefaultDict[str, list[Recording]] = defaultdict(list)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.app_state = app_state

    def build_buffer(self) -> dict[str, int]:
        """Populate the in-memory cache for all saved word recordings."""
        result: dict[str, int] = {}

        for word_dir in self.path.iterdir():
            if not word_dir.is_dir():
                continue

            word_key = self._sanitize_word(word_dir.name)
            self._buffered_read_word(word_key)
            result[word_key] = len(self.buffer[word_key])

        return result

    def load_waves_for(self, word: str) -> Result[list[NDArray[np.float32]], Exception]:
        """Load recordings for a single word, newest first."""
        try:
            word_key = self._sanitize_word(word)

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
            word_key = self._sanitize_word(word)
            word_dir = self.path / word_key
            word_dir.mkdir(parents=True, exist_ok=True)

            saved_count = 0
            now = int(time.time())

            for index, wave in enumerate(waves):
                file_path = word_dir / f"{now}_{index}.wav"
                self.logger.debug(f"Saving wav at {file_path}")
                self._buffered_write(word_key, file_path, wave)
                saved_count += 1

            return Success(saved_count)

        except Exception as exc:
            self.logger.error(f"Encountered error while saving waves: {exc}")
            return Failure(exc)

    def save_wave_async(self, audio: NDArray[np.float32]) -> Result[int, Exception]:
        """Save a single waveform to disk in a background thread without blocking."""
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            file_path = self.path / f"raw_{time.time_ns()}.wav"
            self.logger.debug(f"Scheduling async save for {file_path}")
            self._queue_async_write(file_path, np.asarray(audio, dtype=np.float32).copy())
            return Success(1)
        except Exception as exc:
            self.logger.error(f"Encountered error while scheduling async save: {exc}")
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

    def _sanitize_word(self, word: str) -> str:
        return re.sub(r'[<>:\".,\'/\\|?*\x00-\x1f]', '', word).strip().lower()

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
        self.buffer[word].append(
            Recording(
                sampling_rate=self.sampling_rate,
                timestamp=timestamp,
                wav=audio_copy,
                path=path,
            )
        )
        self._queue_async_write(path, audio_copy)

    def _queue_async_write(self, path: Path, audio: NDArray[np.float32]) -> None:
        future = self._executor.submit(self._async_write_file, path, audio)
        future.add_done_callback(lambda fut, p=path: self._handle_async_write_result(fut, p))

    def _async_write_file(self, path: Path, audio: NDArray[np.float32]) -> None:
        wavfile.write(path, self.sampling_rate, audio)
        self.logger.debug(f"Async save completed for {path}")

    def _handle_async_write_result(self, future: Future, path: Path) -> None:
        exc = future.exception()
        if exc is not None:
            self.logger.error(f"Async save failed for {path}: {exc}")

    def flush_buffer(self) -> None:
        """Wait for all pending async writes to complete before shutdown."""
        self.logger.info("Flushing DiskIO buffer...")
        self._executor.shutdown(wait=True)
        self.logger.info("DiskIO buffer flushed")

