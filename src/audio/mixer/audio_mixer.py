from functools import reduce
import threading
from dataclasses import dataclass, field
from typing import Optional

from audio.plugins.audio_plugins import AudioPlugin
import numpy as np
from numpy.typing import NDArray
import sounddevice as sd
from config import PHONE_CHANNEL, SPEAKER_CHANNEL, CHANNEL, PLAYBACK_BLOCKSIZE, SAMPLERATE
from util.logger import Logger


def singleton(cls):
    """Thread-safe singleton decorator."""
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@dataclass
class AudioQueueElement:
    audio: NDArray[np.float32]
    pos: int = 0


@singleton
class Mixer:
    """Thread-safe stereo mixer that plays queued float32 numpy arrays.

    - Left channel is channel 0, right channel is channel 1.
    - `queue_phone` and `queue_speaker` accept 1-D numpy arrays of dtype float32.
    """

    def __init__(
            self,
            logger: Logger,
            post_mixer_chain: list[AudioPlugin] = [],
            sample_rate: int = SAMPLERATE,
            blocksize: int = PLAYBACK_BLOCKSIZE,
        ) -> None:
        self.logger = logger
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.channels = 2
        self.telephone_channel = PHONE_CHANNEL
        self.speaker_channel = SPEAKER_CHANNEL

        self.post_mixer_chain: list[AudioPlugin] = post_mixer_chain

        self._audio_queue: list[list[AudioQueueElement]] = [[], []]
        self._lock = threading.Lock()

        self._frames_queued: list[int] = [0, 0]
        self._frames_played: list[int] = [0, 0]

        self._stream: sd.OutputStream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(
            self,
            outdata: NDArray[np.float32],
            frames: int,
            time: object,
            status: sd.CallbackFlags,
        ) -> None:
        to_speaker = np.zeros((frames, self.channels), dtype=np.float32)

        # We process however many frames we process, thank you SoundDevice
        with self._lock:
            for channel in (0, 1):
                play_head = 0

                for audio_to_play in self._audio_queue[channel]:
                    if play_head >= frames: # nvm
                        break

                    samples_needed = frames - play_head
                    samples_available = len(audio_to_play.audio) - audio_to_play.pos
                    samples_to_copy = min(samples_needed, samples_available)

                    to_speaker[play_head:play_head + samples_to_copy, channel] += (
                        audio_to_play.audio[audio_to_play.pos:audio_to_play.pos + samples_to_copy]
                    )

                    audio_to_play.pos += samples_to_copy
                    play_head += samples_to_copy

                # Update the remaining audio
                self._audio_queue[channel] = [b for b in self._audio_queue[channel] if b.pos < len(b.audio)]
                self._frames_played[channel] += play_head

        # Doing my favorite thing ever
        to_speaker = reduce(lambda audio, plugin: plugin.process(audio), self.post_mixer_chain, to_speaker)
        outdata[:] = to_speaker

    def _queue_audio(
            self,
            channel: CHANNEL,
            audio: NDArray[np.float32],
            playback_finished: Optional[threading.Event] = None,
        ) -> None:
        if audio.ndim != 1:
            audio = audio.ravel()
        audio = np.asarray(audio, dtype=np.float32).copy()

        with self._lock:
            pending = self._frames_queued[channel.value] - self._frames_played[channel.value]
            wait_time = (pending + len(audio)) / self.sample_rate

            self._frames_queued[channel.value] += len(audio)
            self._audio_queue[channel.value].append(AudioQueueElement(audio=audio))

        if playback_finished is not None:
            self.logger.debug(f"Pending frames: {pending}, new frames: {len(audio)}, wait: {wait_time:.3f}s")
            threading.Timer(wait_time, playback_finished.set).start()

    def queue_phone(
            self,
            audio: NDArray[np.float32],
            playback_finished: Optional[threading.Event] = None,
        ) -> None:
        self._queue_audio(PHONE_CHANNEL, audio, playback_finished)

    def queue_speaker(
            self,
            audio: NDArray[np.float32],
            playback_finished: Optional[threading.Event] = None,
        ) -> None:
        self._queue_audio(SPEAKER_CHANNEL, audio, playback_finished)

    def play_phone_blocking(self, audio: NDArray[np.float32]) -> None:
        self.logger.debug("Blocking for audio on phone")
        synchronization_event = threading.Event()
        self.queue_phone(audio, synchronization_event)
        synchronization_event.wait()

    def play_speaker_blocking(self, audio: NDArray[np.float32]) -> None:
        self.logger.debug("Blocking for audio on speaker")
        synchronization_event = threading.Event()
        self.queue_speaker(audio, synchronization_event)
        synchronization_event.wait()

    def _clear_channel(self, channel: CHANNEL) -> None:
        with self._lock:
            self._audio_queue[channel.value] = []
            self._frames_queued[channel.value] = 0
            self._frames_played[channel.value] = 0

    def stop_phone(self) -> None:
        self._clear_channel(self.telephone_channel)

    def stop_speaker(self) -> None:
        self._clear_channel(self.speaker_channel)

    def stop_all(self) -> None:
        with self._lock:
            self._audio_queue = [[], []]
            self._frames_queued = [0, 0]
            self._frames_played = [0, 0]

    def close(self) -> None:
        """Stop and close the output stream."""
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass

    def __enter__(self) -> "Mixer":
        return self

    def __exit__(self, exc_type: type, exc: Exception, tb: object) -> None:
        self.close()