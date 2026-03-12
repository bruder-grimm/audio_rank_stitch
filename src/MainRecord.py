import threading
from time import time

from audio.DiskIO import DiskIO
from audio.playback_record.Record import Recorder
from audio.playback_record.RecordingQueue import RecordingQueue
from audio.Transcribe import Transcribe
from ui.RecordingWindow import RecordingWindow
from util.Logger import Logger

from scipy.io import wavfile

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

    transcriber = Transcribe(8, logger, SAMPLERATE, device="cpu")
    disk_io = DiskIO(PATH, logger, SAMPLERATE)

    app = RecordingWindow(recorder, logger)
    def worker():
        while True:
            last_recording = recording_queue.get()
            if last_recording is not None:
                app.set_last_sentence("Transcribing...")
                wavfile.write((PATH / f"{int(time())}.wav"), SAMPLERATE, last_recording)
                transcription = transcriber.transcribe(last_recording)
                if transcription.is_failure():
                    continue
                app.set_last_sentence("Aligning...")

                transcript, alignment_result = transcription.get_value()
                words_with_audio = transcriber.get_words_with_audio(last_recording, alignment_result)
                app.set_last_sentence("Saving audio to disk...")
                disk_io.save_waves(words_with_audio)
                app.set_last_sentence(transcript)
            
            threading.Event().wait(1)

    threading.Thread(target=worker, daemon=True).start()
    app.mainloop()