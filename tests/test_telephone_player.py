import numpy as np
from util.logger import Logger, LogLevel
from audio.telephone_playback import TelephonePlayer


class DummyMixer:
    def __init__(self):
        self.calls = []

    def queue_phone(self, audio, playback_finished=None):
        self.calls.append(("queue_phone", audio.shape if hasattr(audio, "shape") else None))

    def play_phone_blocking(self, audio):
        self.calls.append(("play_phone_blocking", audio.shape if hasattr(audio, "shape") else None))


def test_telephone_player_play_silence_async():
    mixer = DummyMixer()
    player = TelephonePlayer(mixer, samplerate=44100)

    player.play_silence_async(0.01)
    assert mixer.calls and mixer.calls[-1][0] == "queue_phone"


def test_telephone_player_play_async_converts_audio():
    mixer = DummyMixer()
    player = TelephonePlayer(mixer, samplerate=44100)

    audio = np.ones((2, 4), dtype=np.float32)
    player.play_async(audio)
    assert mixer.calls[-1][0] == "queue_phone"
