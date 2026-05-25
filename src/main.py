#!/usr/bin/env python
"""
Unified entry point for audio_rank_stitch application.

Runs both recording and playback servers in a single process with shared state.
"""

import signal
import socket
import sys
import threading

from audio.loading.audio_disk_io import DiskIO
from audio.mixer.audio_mixer import Mixer
from audio.telephone_playback import TelephonePlayer
from audio.telephone_record import Recorder
from audio.recording_queue import RecordingQueue
from audio.audio_transcription import Transcribe
from audio.speaker_playback import SpeakerPlayer
from ranking.word_rankings import Rankings
from shuffling.shuffling import Shuffle
from ui.telephone_recording_server import RecordingFrontend
from ui.speaker_playback_server import PlaybackSettingsFrontend
from util.Logger import Logger
from workers.record_worker import run_record_worker
from workers.playback_worker import run_playback_worker
from app_state import AppState

from config import LOGLEVEL, SAMPLERATE, PATH, INSTRUCTIONS


def main():
    """Initialize and run the unified audio_rank_stitch application."""
    
    # Setup logging
    logger = Logger(LOGLEVEL)
    logger.info("=" * 60)
    logger.info("Starting audio_rank_stitch (unified mode)")
    logger.info("=" * 60)
    
    # Initialize shared state
    app_state = AppState()
    logger.info("AppState initialized")
    
    # Initialize shared audio components
    mixer = Mixer()
    logger.info("Mixer initialized")
    
    # Initialize I/O layers with AppState
    disk_io = DiskIO(PATH, logger, SAMPLERATE, app_state=app_state)
    
    logger.info("DiskIO and RankIO initialized with AppState")
    
    # Eagerly load rankings from disk on startup because that's when we have time
    initial_rankings = rank_io.load_rankings().or_else(rank_io.generate_rankings)
    if initial_rankings.is_success():
        logger.info(f"Loaded {len(initial_rankings.get_value())} words from rankings")
    else:
        logger.warn("No initial rankings found - starting with empty rankings")
    
    # Load playback settings from disk (eager load). THIS DOESN't EXIST YET!!
    settings_file = PATH / "settings.json"
    rankings_file = PATH / "rankings.json"

    rankings = Rankings.load(rankings_file)
    app_state.load_settings(settings_file)
    logger.info("Playback settings loaded")
    
    # ===== RECORDING SETUP =====
    recording_queue = RecordingQueue(logger)
    recorder = Recorder(recording_queue, samplerate=SAMPLERATE, channels=1, logger=logger)
    transcriber = Transcribe(8, logger, SAMPLERATE, device="cpu")
    recording_frontend = RecordingFrontend(recorder=recorder, app_state=app_state)
    
    logger.info("Recording components initialized")
    
    # ===== PLAYBACK SETUP =====
    telephone_player = TelephonePlayer(mixer, SAMPLERATE)
    speaker_player = SpeakerPlayer(mixer, SAMPLERATE)
    playback_frontend = PlaybackSettingsFrontend(app_state=app_state)
    
    logger.info("Playback components initialized")
    
    # ===== START WORKERS =====
    record_worker_thread = threading.Thread(
        target=run_record_worker,
        args=(
            app_state,
            recording_queue,
            transcriber,
            disk_io,
            telephone_player,
            recording_frontend,
            logger,
        ),
        daemon=True,
        name="RecordWorker",
    )
    record_worker_thread.start()
    logger.info("Record worker thread started")
    
    playback_worker_thread = threading.Thread(
        target=run_playback_worker,
        args=(
            app_state,
            rank_io,
            disk_io,
            speaker_player,
            playback_frontend,
            logger,
        ),
        daemon=True,
        name="PlaybackWorker",
    )
    playback_worker_thread.start()
    logger.info("Playback worker thread started")
    
    # ===== START FLASK SERVERS =====
    recording_flask_thread = threading.Thread(
        target=recording_frontend.run,
        kwargs={"debug": False},
        daemon=True,
        name="RecordingFlask",
    )
    recording_flask_thread.start()
    logger.info("RecordingFrontend started on http://localhost:5001")
    
    playback_flask_thread = threading.Thread(
        target=playback_frontend.run,
        kwargs={"debug": False},
        daemon=True,
        name="PlaybackFlask",
    )
    playback_flask_thread.start()
    logger.info(f"PlaybackSettingsFrontend started on http://{socket.gethostbyname(socket.gethostname())}:5000")
    
    # ===== SIGNAL HANDLERS =====
    def signal_handler(signum, frame):
        """Handle graceful shutdown on SIGINT (Ctrl+C)."""
        logger.info("\n" + "=" * 60)
        logger.info("Received shutdown signal, initiating graceful shutdown...")
        logger.info("=" * 60)
        
        # Signal workers to stop
        app_state.shutdown_requested.set()
        logger.info("Shutdown signal sent to workers")
        
        # Wait for workers to finish current operations
        logger.info("Waiting for workers to finish...")
        threading.Event().wait(2)
        
        # Flush disk I/O (wait for async writes)
        disk_io.flush_buffer()
        logger.info("Disk I/O flushed")
        
        # Persist rankings to disk
        logger.info("Persisting rankings to disk...")
        rank
        logger.info("Rankings persisted")
        
        # Persist playback settings to disk
        logger.info("Persisting playback settings...")
        app_state.persist_settings(PATH / "settings.json")
        logger.info("Settings persisted")
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # ===== MAIN LOOP =====
    logger.info("=" * 60)
    logger.info("Application running. Press Ctrl+C to quit.")
    logger.info("Recording: http://localhost:5001")
    logger.info("Playback: http://localhost:5000")
    logger.info("=" * 60)
    
    try:
        # Keep the main thread alive
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
