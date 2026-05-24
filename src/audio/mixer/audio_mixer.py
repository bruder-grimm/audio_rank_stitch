import threading
from typing import List

import numpy as np
from numpy.typing import NDArray
import sounddevice as sd
from config import PHONE_CHANNEL, SPEAKER_CHANNEL, CHANNEL, PLAYBACK_BLOCKSIZE, SAMPLERATE


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
    - Multiple buffers queued on the same channel will be mixed (overlapped).
    """

    def __init__(self, sample_rate: int = SAMPLERATE, blocksize: int = PLAYBACK_BLOCKSIZE):
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.channels = 2
        self.telephone_channel = PHONE_CHANNEL
        self.speaker_channel = SPEAKER_CHANNEL

        # Each channel keeps a list of active buffers: dicts with 'audio' and 'pos'.
        self._buffers: List[List[dict]] = [[], []]
        self._lock = threading.Lock()

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        # Fill output buffer by summing active buffers per channel.
        out = np.zeros((frames, self.channels), dtype=np.float32)

        with self._lock:
            for ch in (0, 1):
                buffers = self._buffers[ch]
                out_offset = 0  # Track position in output buffer
                i = 0
                while i < len(buffers) and out_offset < frames:
                    buf = buffers[i]
                    arr = buf["audio"]
                    pos = buf["pos"]
                    remaining = arr.shape[0] - pos
                    if remaining <= 0:
                        # finished buffer, remove it
                        buffers.pop(i)
                        continue

                    # Only fill remaining space in output buffer
                    frames_available = frames - out_offset
                    to_take = min(frames_available, remaining)
                    out[out_offset:out_offset + to_take, ch] += arr[pos : pos + to_take]
                    buf["pos"] += to_take
                    out_offset += to_take

                    if buf["pos"] >= arr.shape[0]:
                        buffers.pop(i)
                    else:
                        i += 1

        # Write mixed output to outdata
        outdata[:] = out

    def _queue_audio(self, channel: CHANNEL, audio: NDArray[np.float32]) -> None:
        if audio.ndim != 1:
            audio = audio.ravel()
        arr = np.asarray(audio, dtype=np.float32).copy()
        if arr.size == 0:
            return
        with self._lock:
            self._buffers[channel.value].append({"audio": arr, "pos": 0})

    def queue_phone(self, audio: NDArray[np.float32]) -> None:
        self._queue_audio(PHONE_CHANNEL, audio)

    def queue_speaker(self, audio: NDArray[np.float32]) -> None:
        self._queue_audio(SPEAKER_CHANNEL, audio)

    def stop(self) -> None:
        """Stop playback and clear queued buffers."""
        with self._lock:
            self._buffers = [[], []]

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

    
