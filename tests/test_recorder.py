import numpy as np
from util.logger import Logger, LogLevel
from audio.telephone_record import Recorder, StreamClosedError, RecordingError


def test_stop_and_get_recording_without_stream_returns_failure(capsys):
    recorder = Recorder(Logger(level=LogLevel.DEBUG))
    result = recorder.stop_and_get_recording()

    assert result.is_failure()
    assert isinstance(result.get_error(), StreamClosedError)
    assert "Stream was not open" in capsys.readouterr().out


def test_normalize_audio_silence_remains_silent():
    recorder = Recorder(Logger(level=LogLevel.DEBUG))
    silence = np.zeros((10, 1), dtype=np.float32)
    normalized = recorder._normalize_audio(silence)
    assert np.allclose(normalized, silence)


def test_normalize_audio_scales_to_target_rms():
    recorder = Recorder(Logger(level=LogLevel.DEBUG))
    audio = np.array([0.5, -0.5, 0.25, -0.25], dtype=np.float32)
    normalized = recorder._normalize_audio(audio, target_rms=0.1)
    assert np.isfinite(normalized).all()
