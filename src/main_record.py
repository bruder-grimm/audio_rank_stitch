import threading
from time import time

from audio.audio_disk_io import DiskIO
from audio.mixer.audio_mixer import Mixer
from audio.telephone_playback import TelephonePlayer
from audio.telephone_record import Recorder
from audio.recording_queue import RecordingQueue
from audio.audio_transcription import Transcribe
from ui.telephone_recording_server import RecordingFrontend
from util.logger import Logger

from scipy.io import wavfile

from config import LOGLEVEL, SAMPLERATE, PATH, INSTRUCTIONS


if __name__ == "__main__":

    # We need to get the recorder up
    # The recorder hooks into the Window
    # when a recording was stopped we transcribe and align
    # we save the files but keep everything in flight
    # window gets updated with last spoken sentence
    # repeat
    logger = Logger(LOGLEVEL)
    mixer = Mixer()
    
    recording_queue = RecordingQueue(logger)
    recorder = Recorder(recording_queue, samplerate=SAMPLERATE, channels=1, logger=logger)

    player = TelephonePlayer(mixer, SAMPLERATE)

    transcriber = Transcribe(8, logger, SAMPLERATE, device="cpu")
    disk_io = DiskIO(PATH, logger, SAMPLERATE)

    # Initialize instruction state
    state = {
        "instruction_index": 0,
        "current_instruction": INSTRUCTIONS[0],
        "last_recording": []
    }
    
    app = RecordingFrontend(recorder=recorder, initial_instruction=state["current_instruction"])
    
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=app.run, kwargs={"debug": False}, daemon=True)
    flask_thread.start()
    logger.info("RecordingFrontend started on http://localhost:5001")
    
    def worker():
        while True:
            last_recording = recording_queue.get()
            if last_recording is not None:
                app.set_background_color("#ffffff")
                disk_io.save_wave(last_recording)
                state["last_recording"] = last_recording
                
                transcription = transcriber.transcribe(last_recording)
                if transcription.is_failure():
                    continue

                transcript, alignment_result = transcription.get_value()
                words_with_audio = transcriber.get_words_with_audio(last_recording, alignment_result)
                disk_io.save_waves(words_with_audio)

                logger.info(f"Sentence transcribed: {transcript}")
                
                # Cycle to next instruction
                state["instruction_index"] = (state["instruction_index"] + 1) % len(INSTRUCTIONS)
                state["current_instruction"] = INSTRUCTIONS[state["instruction_index"]]
                app.set_prompt(state["current_instruction"])
                app.set_background_color("#ffffff")
            
            threading.Event().wait(1)

    threading.Thread(target=worker, daemon=True).start()