import shutil
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from util.logger import Logger, LogLevel
from util.result import Failure, Success
from audio.loading.audio_disk_io import DiskIO, NoRecordingsError, SamplingRateMismatch


def test_save_wave_and_get_latest_raw_recording(tmp_path):
    logger = Logger(level=LogLevel.DEBUG)
    disk_io = DiskIO(tmp_path, logger, sampling_rate=44100)
    audio = np.zeros(100, dtype=np.float32)

    save_result = disk_io.save_wave(audio)
    assert save_result.is_success()
    assert save_result.get_value() == 1

    latest = disk_io.get_latest_raw_recording()
    assert latest.is_success()
    assert latest.get_value().shape == (100,)


def test_get_latest_raw_recording_no_files_returns_failure(tmp_path):
    logger = Logger(level=LogLevel.DEBUG)
    disk_io = DiskIO(tmp_path, logger, sampling_rate=44100)

    result = disk_io.get_latest_raw_recording()
    assert result.is_failure()
    assert isinstance(result.get_error(), NoRecordingsError)


def test_get_latest_raw_recording_sampling_rate_mismatch(tmp_path):
    logger = Logger(level=LogLevel.DEBUG)
    other_path = tmp_path / "raw_123.wav"
    wavfile.write(other_path, 22050, np.zeros(10, dtype=np.float32))

    disk_io = DiskIO(tmp_path, logger, sampling_rate=44100)
    result = disk_io.get_latest_raw_recording()
    assert result.is_failure()
    assert isinstance(result.get_error(), SamplingRateMismatch)
