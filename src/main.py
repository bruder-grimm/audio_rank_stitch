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
from audio.audio_transcription import Transcribe
from audio.speaker_playback import SpeakerPlayer
from ranking.rankings import Rankings
from ui.telephone_recording_server import RecordingFrontend
from ui.speaker_playback_server import PlaybackSettingsFrontend
from util.logger import Logger
from workers.record_worker import run_record_worker
from workers.playback_worker import run_playback_worker
from app_state import AppState

from config import LOGLEVEL, SAMPLERATE, AUDIO_SNIPPET_PATH


def main():
    """Initialize and run the unified audio_rank_stitch application."""
    
    # Setup logging
    logger = Logger(LOGLEVEL)
    logger.info("=" * 60)
    logger.info("Starting audio_rank_stitch (unified mode)")
    logger.info("=" * 60)

    rankings = Rankings(logger=logger)
    app_state = AppState(rankings, settings_path=AUDIO_SNIPPET_PATH / "settings.json")

    rankings.build_rankings_from_disk(AUDIO_SNIPPET_PATH)
    logger.info("Playback settings loaded, rankings initialized, and AppState created")
    
    # Initialize shared audio components
    mixer = Mixer()
    logger.info("Mixer initialized")
    
    # Initialize Disk I/O 
    disk_io = DiskIO(AUDIO_SNIPPET_PATH, logger, SAMPLERATE)
    disk_io.build_buffer_from_disk()
    logger.info("DiskIO initialized and buffer built with recordings from disk")
    

    # ===== RECORDING SETUP =====
    telephone_recorder = Recorder(samplerate=SAMPLERATE, channels=1, logger=logger)
    telephone_player = TelephonePlayer(mixer, samplerate=SAMPLERATE)
    transcriber = Transcribe(batch_size = 8, logger=logger, samplerate=SAMPLERATE, device="cpu")
    recording_frontend = RecordingFrontend(recorder=telephone_recorder, app_state=app_state)
    
    logger.info("Recording components initialized")
    
    # ===== PLAYBACK SETUP =====
    speaker_player = SpeakerPlayer(mixer, samplerate=SAMPLERATE)
    playback_frontend = PlaybackSettingsFrontend(app_state=app_state)
    
    logger.info("Playback components initialized")
    
    # ===== START WORKERS =====
    record_worker_thread = threading.Thread(
        target=run_record_worker,
        args=(
            app_state,
            disk_io,
            telephone_player,
            telephone_recorder,
            transcriber,
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
            disk_io,
            speaker_player,
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
        app_state.shutdown()
        logger.info("Shutdown signal sent to workers")
        
        # Wait for workers to finish current operations
        logger.info("Waiting for workers to finish...")
        threading.Event().wait(2)
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # ===== MAIN LOOP =====
    logger.info("=" * 60)
    logger.info("Application running. Press Ctrl+C to quit.")
    logger.info("=" * 60)
    
    try:
        # Keep the main thread alive
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
