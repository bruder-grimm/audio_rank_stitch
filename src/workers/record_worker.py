"""Recording worker thread for capturing and transcribing audio."""

import threading
from typing import Optional
from audio.loading.audio_disk_io import DiskIO
from audio.telephone_record import Recorder
from audio.recording_queue import RecordingQueue
from audio.audio_transcription import Transcribe
from config import INSTRUCTIONS
from numpy.typing import NDArray
from ui.telephone_recording_server import RecordingFrontend
from util.logger import Logger
from app_state import AppState
import numpy as np


def run_record_worker(
    app_state: AppState,
    recording_queue: RecordingQueue,
    transcriber: Transcribe,
    disk_io: DiskIO,
    flask_frontend: RecordingFrontend,
    logger: Logger,
) -> None:
    """
    Worker thread that processes recordings from the queue.
    
    Runs in a loop until app_state.stop_event is set.
    Transcribes audio, extracts word segments, saves to disk, and caches in AppState.
    Updates rankings and Flask frontend as new words are added.
    """
    while not app_state.shutdown_requested.is_set():
        last_recording = recording_queue.get()
        if last_recording is None:
            threading.Event().wait(0.1)
            continue

        process_recording(
            recording=last_recording,
            flask_frontend=flask_frontend,
            disk_io=disk_io,
            transcriber=transcriber,
            app_state=app_state,
            logger=logger
        )
        # Cycle to next instruction
        state["instruction_index"] = (state["instruction_index"] + 1) % len(INSTRUCTIONS)
        state["current_instruction"] = INSTRUCTIONS[state["instruction_index"]]
        flask_frontend.set_prompt(state["current_instruction"])
        flask_frontend.set_background_color("#ffffff")
        
        threading.Event().wait(0.1)
    
    logger.info("Record worker shutting down...")

def process_recording(
        recording: NDArray[np.float32], 
        flask_frontend: RecordingFrontend,
        disk_io: DiskIO,
        transcriber: Transcribe,
        app_state: AppState,
        logger: Logger
    ) -> None:
        flask_frontend.set_background_color("#ffffff")
        disk_io.save_wave_async(recording)
        
        transcription = transcriber.transcribe(recording)
        if transcription.is_failure():
            threading.Event().wait(0.1)
            continue

        transcript, alignment_result = transcription.get_value()
        words_with_audio = transcriber.get_words_with_audio(recording, alignment_result)
        
        # Save words and update rankings
        result = disk_io.save_waves(words_with_audio)
        if result.is_success():
            # Update rankings in AppState for each word
            for word in words_with_audio.keys():
                count = len(words_with_audio[word])
                app_state.increment_ranking(word, count)
                logger.info(f"Updated ranking for '{word}': +{count}")

        logger.info(f"Sentence transcribed: {transcript}")