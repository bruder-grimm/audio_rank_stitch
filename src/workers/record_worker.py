"""Recording worker thread for capturing and transcribing audio."""

import threading
import time
from typing import Optional
from audio.loading.audio_disk_io import DiskIO
from audio.telephone_playback import TelephonePlayer
from audio.telephone_record import Recorder
from audio.audio_transcription import Transcribe
from numpy.typing import NDArray
from ui.telephone_recording_server import RecordingFrontend
from util.logger import Logger
from app_state import AppState
import numpy as np
from config import PRE_DIAL_DELAY_SECONDS, POST_RECORDING_PROCESSING_DELAY_SECONDS


def run_record_worker(
    app_state: AppState,
    disk_io: DiskIO,
    phone_player: TelephonePlayer,
    phone_recorder: Recorder,
    transcriber: Transcribe,
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
        last_recording: Optional[NDArray[np.float32]] = None

        # Wait until the phone is picked up
        if not app_state.phone_picked_up.is_set():
            threading.Event().wait(0.1)
            continue

        # Phone was picked up, start the interaction
        # All of the audio here is queued and we return control to this script immediately.
        dialing_beep_event = threading.Event()
        last_recording_event = threading.Event()
        flask_frontend.set_background_color("#dd00ff")
        phone_player.play_silence_async(PRE_DIAL_DELAY_SECONDS)
        phone_player.play_dialing_start_beep_async(dialing_beep_event)
        
        event_to_check = last_recording_event if last_recording is not None else dialing_beep_event
        if last_recording is not None:
            phone_player.play_async(last_recording, last_recording_event)
        
        while not event_to_check.is_set():
            if not app_state.phone_picked_up.is_set():
                revert_to_idle_state(flask_frontend, phone_player)
                continue

        flask_frontend.set_background_color("#ff0000")
        phone_player.play_recording_start_beep()
        
        phone_recorder.start_recording()
        while app_state.should_record.is_set():
            threading.Event().wait(0.1)

        # We're done recording, process the audio
        flask_frontend.set_background_color("#000000")
        
        start_time = time.time()
        possible_next_recording = phone_recorder.stop_and_get_recording().map(
            lambda recording: process_recording(recording, disk_io, transcriber, app_state, logger)
        )
        processing_time = time.time() - start_time

        # If processing the recording failed, log the error and revert to idle state
        if possible_next_recording.is_failure():
            logger.error(f"Failed to process recording: {possible_next_recording.get_error()}")
            revert_to_idle_state(flask_frontend, phone_player)
            continue
        
        logger.debug(f"Processing time for recording: {processing_time:.2f} seconds")

        # Otherwise, we successfully processed the recording and can now taint the player
        # and update the instruction for the next person
        app_state.cycle_instruction()
        app_state.playback_dirty.set()

        threading.Event().wait(max(0, POST_RECORDING_PROCESSING_DELAY_SECONDS - processing_time))
        flask_frontend.set_background_color("#ffffff")
    
    logger.info("Record worker shutting down...")

def revert_to_idle_state(flask_frontend: RecordingFrontend, phone_player: TelephonePlayer):
    """Helper function to revert to idle state when phone is hung up."""
    phone_player.clear_queue()
    flask_frontend.set_background_color("#ffffff")

def process_recording(
    recording: NDArray[np.float32], 
    disk_io: DiskIO,
    transcriber: Transcribe,
    app_state: AppState,
    logger: Logger
) -> None:
    disk_io.save_wave(recording).on_failure(
        lambda error: logger.error(f"Failed to save full recording: {error}")
    )
    
    transcription = transcriber.transcribe(recording)
    if transcription.is_failure():
        logger.error(f"Transcription failed: {transcription.get_error()}")
        return
    
    transcript, alignment_result = transcription.get_value()
    words_with_audio = transcriber.get_words_with_audio(recording, alignment_result)
    
    # Save words and update rankings
    result = disk_io.save_waves(words_with_audio)
    if result.is_failure():
        logger.error(f"Failed to save word snippets: {result.get_error()}")
        return
    
    for word in words_with_audio.keys():
        count = len(words_with_audio[word])
        app_state.increment_ranking(word, count)
        logger.info(f"Updated ranking for '{word}': +{count}")
    
    app_state.heapify_rankings()
    logger.info(f"Sentence transcribed: {transcript}")