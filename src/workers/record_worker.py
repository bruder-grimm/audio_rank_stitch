"""Recording worker thread for capturing and transcribing audio."""

import threading
import time
from typing import Optional
from audio.loading.audio_disk_io import DiskIO
from audio.loading.filename import get_key_from_word
from audio.telephone_playback import TelephonePlayer
from audio.telephone_record import Recorder
from audio.audio_transcription import Transcribe
from audio.speech_detection import SpeechDetector
from numpy.typing import NDArray
from ui.telephone_recording_server import RecordingFrontend
from util.logger import Logger
from app_state import AppState
import numpy as np
from config import PRE_DIAL_DELAY_SECONDS, POST_RECORDING_PROCESSING_DELAY_SECONDS

from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)


def run_record_worker(
    app_state: AppState,
    disk_io: DiskIO,
    phone_player: TelephonePlayer,
    phone_recorder: Recorder,
    transcriber: Transcribe,
    speech_detector: SpeechDetector,
    flask_frontend: RecordingFrontend,
    logger: Logger,
) -> None:
    """
    Worker thread that processes recordings from the queue.
    
    Runs in a loop until app_state.stop_event is set.
    Transcribes audio, extracts word segments, saves to disk, and caches in AppState.
    Updates rankings and Flask frontend as new words are added.
    """
    last_recording: Optional[NDArray[np.float32]] = disk_io.get_latest_raw_recording().to_optional()

    while not app_state.shutdown_requested.is_set():

        # Wait until the phone is picked up
        if not app_state.phone_picked_up.is_set():
            time.sleep(0.1)
            continue

        logger.info("Phone was picked up")

        # Phone was picked up, start the interaction
        # All of the audio here is queued and we return control to this script immediately.
        dialing_beep_played = threading.Event()
        last_recording_played = threading.Event()
        flask_frontend.set_background_color("#c913ba")
        phone_player.play_silence_async(PRE_DIAL_DELAY_SECONDS)
        logger.debug("Queueing dialing beep")
        phone_player.play_dialing_start_beep_async(dialing_beep_played)
        
        event_to_check = last_recording_played if last_recording is not None else dialing_beep_played
        if last_recording is not None:
            logger.debug("Queueing recording of the last person")
            phone_player.play_async(last_recording, last_recording_played)
        

        while not event_to_check.is_set():
            time.sleep(0.1)
            if not app_state.phone_picked_up.is_set():
                event_to_check.set()
                revert_to_idle_state(flask_frontend, phone_player)
                break
        if not app_state.phone_picked_up.is_set():
            logger.info("Phone was put down prematurely")
            continue

        event_to_check.wait()
        logger.debug("Done waiting")

        phone_player.play_recording_start_beep()
        flask_frontend.set_background_color("#f20000")
        
        phone_recorder.start_recording()
        while app_state.phone_picked_up.is_set():
            time.sleep(0.1)

        logger.info("Phone was put down after recording was finished")

        # We're done recording, process the audio
        flask_frontend.set_background_color("#000000")
        
        possible_next_recording = phone_recorder.stop_and_get_recording()
        
        # If the next recording was successful, we check if it contains speech.
        # If so, we transcribe, set it as the next recording to listen to
        # And then delete the old recordings!
        possible_next_recording = possible_next_recording.flat_map(
            speech_detector.contains_speech
        )

        if possible_next_recording.is_success():
            next_recording = possible_next_recording.get_value()
            executor.submit(
                process_recording,
                next_recording,
                disk_io,
                transcriber,
                app_state,
                logger
            )

            last_recording = next_recording

            deleted_old_recordings = disk_io.delete_old_raw_recordings()
            if deleted_old_recordings.is_failure():
                logger.info(f"Deleting old recordings failed: {deleted_old_recordings.get_error()}")

        # If processing the recording failed, log the error and revert to idle state
        if possible_next_recording.is_failure():
            logger.info(f"Failed to process recording: {possible_next_recording.get_error()}")
            revert_to_idle_state(flask_frontend, phone_player)
            continue
        
        # Otherwise, we successfully processed the recording and 
        # and update the instruction for the next person
        app_state.cycle_instruction()

        threading.Event().wait(max(0, POST_RECORDING_PROCESSING_DELAY_SECONDS))
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
    start_time = time.time()

    transcription = transcriber.transcribe(recording)
    if transcription.is_failure():
        logger.error(f"Transcription failed: {transcription.get_error()}")
        return
    
    sentence = get_key_from_word(transcription.get_value()[0].lower())
    
    disk_io.save_transcription(sentence).on_failure(
        lambda error: logger.error(f"Failed to save transcription: {error}")
    )

    transcript, alignment_result = transcription.get_value()
    words_with_audio = transcriber.get_words_with_audio(
        recording,
        alignment_result,
    )


    vocabulary = list(words_with_audio.keys())
    vocabulary = [get_key_from_word(word) for word in vocabulary]
    
    # Save words and update rankings
    result = disk_io.save_waves(words_with_audio)
    if result.is_failure():
        logger.error(f"Failed to save word snippets: {result.get_error()}")
        return
    
    classified_words = app_state.embeddings_provider.as_words_with_class(vocabulary)
    logger.debug(f"Training on classified words: {classified_words}")

    app_state.markov_model.update(classified_words)
    app_state.rankings.update(classified_words)
    app_state.rankings.heapify()
    app_state.playback_dirty.set()

    processing_time = time.time() - start_time
    logger.debug(f"Processing time for recording: {processing_time:.2f} seconds")

    logger.info(f"Sentence transcribed: {transcript}")