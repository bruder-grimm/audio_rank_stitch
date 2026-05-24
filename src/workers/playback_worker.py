"""Playback worker thread for playing ranked audio."""

import threading
from audio.audio_disk_io import DiskIO
from audio.speaker_playback import SpeakerPlayer
from ranking import word_ranking
from ranking.word_ranking_io import RankIO
from shuffling.shuffling import Shuffle
from util.logger import Logger
from app_state import AppState


def run_playback_worker(
    app_state: AppState,
    rank_io: RankIO,
    disk_io: DiskIO,
    audio_player: SpeakerPlayer,
    flask_frontend,
    logger: Logger,
) -> None:
    """
    Worker thread that manages playback of ranked audio snippets.
    
    Runs in a loop until app_state.shutdown_requested is set.
    Loads rankings from AppState, shuffles top-k words, and plays audio.
    """
    while not app_state.shutdown_requested.is_set():
        # Get current UI settings
        current_top_k = flask_frontend.top_k

        # Load rankings from AppState (which is kept in sync with disk)
        rankings = rank_io.load_rankings().or_else(rank_io.generate_rankings)
        
        if rankings.is_failure():
            logger.debug("Couldn't load or generate rankings, skipping shuffle and playback")
            threading.Event().wait(1)
            continue

        # Get top k words
        top_words = word_ranking.top_k(rankings.get_value(), current_top_k)
        flask_frontend.set_words(top_words)
        
        # Load audio snippets for top k words (with AppState caching)
        word_snippets = {
            word: disk_io.load_waves_for(word).get_or_else([])
            for word, _ in top_words
        }

        # Shuffle and prepare for playback
        shuffle = Shuffle(word_snippets, rankings.get_value(), logger)
        top_k = shuffle.get_top_k(current_top_k)
        shuffled = shuffle.shuffle_top_k(top_k, flask_frontend.shuffle_factor)

        # Play if button pressed
        if flask_frontend.play_pressed:
            for audio in shuffled:
                if app_state.pause_pressed.isSet():
                    break
                audio_player.play(
                    audio,
                    attack=app_state.attack,
                    decay=app_state.decay,
                )
                threading.Event().wait(app_state.silence_duration)
        else:
            logger.debug("No audio in playback queue")
            threading.Event().wait(0.5)
    
    logger.info("Playback worker shutting down...")
