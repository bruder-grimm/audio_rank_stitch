import threading

from audio.DiskIO import DiskIO
from audio.Record import Recorder
from audio.RecordingQueue import RecordingQueue
from audio.Transcribe import Transcribe
from ui.RecordingWindow import RecordingWindow
from util.Logger import Logger

from config import LOGLEVEL, SAMPLERATE, PATH


if __name__ == "__main__":

    # We need to get the recorder up
    # The recorder hooks into the Window
    # when a recording was stopped we transcribe and align
    # we save the files but keep everything in flight
    # window gets updated with last spoken sentence
    # repeat
    logger = Logger(LOGLEVEL)
    recording_queue = RecordingQueue(logger)
    recorder = Recorder(recording_queue, samplerate=SAMPLERATE, channels=1, logger=logger)

    transcriber = Transcribe(64, logger, device="cpu")
    disk_io = DiskIO(PATH, logger, SAMPLERATE)

    app = RecordingWindow(recorder, logger)
    def worker():
        while True:
            last_recording = recording_queue.get()
            if last_recording is not None:
                transcription = transcriber.transcribe(last_recording)
                if transcription.is_failure():
                    continue
                logger.debug("we're here")
                words_with_audio = transcriber.get_words_with_audio(last_recording, transcription.get_value(), SAMPLERATE)
                logger.debug("we're there")
                disk_io.save_waves(words_with_audio)
            
            threading.Event().wait(1)

    threading.Thread(target=worker, daemon=True).start()
    app.mainloop()