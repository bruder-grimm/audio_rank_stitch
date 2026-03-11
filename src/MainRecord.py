from audio.Record import Recorder
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

    logger = Logger(LOGLEVEL)
    recorder = Recorder(SAMPLERATE, channels=1, logger=logger)

    app = RecordingWindow(recorder, logger)
    app.mainloop()