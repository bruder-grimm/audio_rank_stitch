"""Playback worker thread for playing ranked audio."""

import threading

from audio.loading.audio_disk_io import DiskIO
from audio.speaker_playback import SpeakerPlayer
from ranking.shuffling import Shuffle
from ui.speaker_playback_server import PlaybackSettingsFrontend
from util.logger import Logger
from app_state import AppState


def run_playback_worker(
    app_state: AppState,
    disk_io: DiskIO,
    audio_player: SpeakerPlayer,
    logger: Logger,
) -> None:
    """
    Worker thread that manages playback of ranked audio snippets.
    
    Runs in a loop until app_state.shutdown_requested is set.
    Loads rankings from AppState, shuffles top-k words, and plays audio.
    """
    while not app_state.shutdown_requested.is_set():
        if not app_state.should_play.is_set():
            threading.Event().wait(0.1)
            continue
        
        # Get top k words with our current top-k settings from AppState
        top_words = app_state._rankings.get_words_for_topk_range(app_state.top_k_a, app_state.top_k_b)
        app_state.set_current_top_k_word_selection(top_words)
        
        # Load audio snippets for top k words (with caching - do NOT worry ok thanks)
        word_snippets = {
            word: disk_io.load_waves_for(word).get_or_else([])
            for word, _ in top_words
        }

        # Shuffle and prepare for playback
        shuffler = Shuffle(logger)
        shuffled = shuffler.shuffle_top_k(word_snippets, top_words, app_state.shuffle_factor)

        for audio in shuffled:
            # Stop current playback if should_play is unset during playback
            if not app_state.should_play.is_set():
                audio_player.stop()
                break

            # Don't stop the playback but stop queuing if the data has been touched
            if app_state.playback_dirty.is_set():
                break

            # Block during playback of a single snippet because we don't want to fill our
            # queue with a bunch of audio that is now stale because audio has changed
            audio_player.play_blocking(
                audio,
                attack=app_state.attack,
                decay=app_state.decay,
            )
            # Having this queued is critical: We can actually get a new ranking while we're
            # still playing the current audio in this sort of blanking period, so we can
            # have what is hopefully uninterrupted plaback while we update our snippets
            # with the new audio that has been created by the recording thread!
            audio_player.queue_silence(app_state.silence_duration)
    
    logger.info("Playback worker shutting down...")
