from pathlib import Path
import threading

from audio.DiskIO import DiskIO
from audio.Record import Recorder
from audio.RecordingQueue import RecordingQueue
from audio.Transcribe import Transcribe
from ui.RecordingWindow import RecordingWindow
from util.Logger import LogLevel, Logger


if __name__ == "__main__":

    # We need to get the recorder up
    # The recorder hooks into the Window
    # when a recording was stopped we transcribe and align
    # we save the files but keep everything in flight
    # window gets updated with last spoken sentence
    # repeat
    LOGLEVEL = LogLevel.DEBUG

    SAMPLERATE = 44100

    recording_queue = RecordingQueue()
    logger = Logger(LOGLEVEL)
    recorder = Recorder(recording_queue, samplerate=SAMPLERATE, channels=1, logger=logger)

    transcriber = Transcribe(64, "int16")
    disk_io = DiskIO(Path("./../word_snippets"), logger, SAMPLERATE)

    app = RecordingWindow(recorder, logger)
    def worker():
        while True:
            last_recording = recording_queue.get()
            if last_recording:
                transcription = transcriber.transcribe(last_recording)
                words_with_audio = transcriber.get_words_with_audio(last_recording, transcription, SAMPLERATE)
                disk_io.save_waves(words_with_audio)

    threading.Thread(target=worker, daemon=True).start()

    app.mainloop()