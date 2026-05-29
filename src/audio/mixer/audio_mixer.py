import threading
from typing import List, Optional

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


@singleton
class Mixer:
    """Thread-safe stereo mixer that plays queued float32 numpy arrays.

    - Left channel is channel 0, right channel is channel 1.
    - `play_left` and `play_right` accept 1-D numpy arrays of dtype float32.
    """

    def __init__(self, logger: Logger, sample_rate: int = SAMPLERATE, blocksize: int = PLAYBACK_BLOCKSIZE):
        self.logger = logger
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.channels = 2
        self.telephone_channel = PHONE_CHANNEL
        self.speaker_channel = SPEAKER_CHANNEL

        # Each channel keeps a list of active buffers: dicts with 'audio' and 'pos'.
        self._buffers: List[List[dict]] = [[], []]
        self._lock = threading.Lock()
        
        # It's like playheads but I don't know what I'm doing
        self._frames_queued: List[int] = [0, 0]
        self._frames_played: List[int] = [0, 0]

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        out = np.zeros((frames, self.channels), dtype=np.float32)

        with self._lock:
            for ch in (0, 1):
                frames_consumed = 0
                buffers = self._buffers[ch]
                out_offset = 0
                i = 0
                while i < len(buffers) and out_offset < frames:
                    buf = buffers[i]
                    arr = buf["audio"]
                    pos = buf["pos"]
                    remaining = arr.shape[0] - pos
                    if remaining <= 0:
                        buffers.pop(i)
                        continue

                    to_take = min(frames - out_offset, remaining)
                    out[out_offset:out_offset + to_take, ch] += arr[pos:pos + to_take]
                    buf["pos"] += to_take
                    out_offset += to_take
                    frames_consumed += to_take

                    if buf["pos"] >= arr.shape[0]:
                        buffers.pop(i)
                    else:
                        i += 1

                self._frames_played[ch] += frames_consumed  # advance "playhead"

        outdata[:] = out

    def _queue_audio(
        self,
        channel: CHANNEL,
        audio: NDArray[np.float32],
        playback_finished: Optional[threading.Event] = None,
    ) -> None:
        if audio.ndim != 1:
            audio = audio.ravel()
        arr = np.asarray(audio, dtype=np.float32).copy()

        with self._lock:
            # Frames still waiting to be played + the new audio = total wait
            pending = self._frames_queued[channel.value] - self._frames_played[channel.value]
            wait_frames = pending + len(arr)
            wait_time = wait_frames / self.sample_rate

            self._frames_queued[channel.value] += len(arr)
            self._buffers[channel.value].append({"audio": arr, "pos": 0})

        if playback_finished is not None:
            self.logger.debug(f"Pending frames: {pending}, new frames: {len(arr)}, wait: {wait_time:.3f}s")
            threading.Timer(wait_time, playback_finished.set).start()

    def queue_phone(
            self, 
            audio: NDArray[np.float32], 
            playback_finished: Optional[threading.Event] = None
        ) -> None:
        self._queue_audio(PHONE_CHANNEL, audio, playback_finished)

    def queue_speaker(
            self, 
            audio: NDArray[np.float32], 
            playback_finished: Optional[threading.Event] = None
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

    def stop_phone(self) -> None:
        with self._lock:
            self._buffers[self.telephone_channel.value] = []
            self._frames_queued[self.telephone_channel.value] = 0
            self._frames_played[self.telephone_channel.value] = 0

    def stop_speaker(self) -> None:
        with self._lock:
            self._buffers[self.speaker_channel.value] = []
            self._frames_queued[self.speaker_channel.value] = 0
            self._frames_played[self.speaker_channel.value] = 0

    def stop_all(self) -> None:
        with self._lock:
            self._buffers = [[], []]
            self._frames_queued = [0, 0]
            self._frames_played = [0, 0]

    def close(self) -> None:
        """Stop and close the output stream."""
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    
