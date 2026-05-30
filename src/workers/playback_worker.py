"""Playback worker thread for playing ranked audio."""

import itertools
import random
import threading
import time
from typing import Optional

from audio.loading.audio_disk_io import DiskIO
from audio.speaker_playback import SpeakerPlayer
from config import SENTENCE_LENGTH
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
    queuing_is_go: Optional[threading.Event] = None

    while not app_state.shutdown_requested.is_set():
        if not app_state.should_play.is_set():
            time.sleep(0.1)
            continue

        
        top_words = list(app_state.get_current_top_k_selection().keys())
        logger.debug(f"Top words are: {top_words}")
        new_sentence = app_state.markov_model.generate_from_pool(
            word_pool=top_words, 
            max_words=app_state.sentence_length, 
            temperature=app_state.temperature,
            require_all=True,
            max_retries=100
        )
        if app_state.run_the_list:
            new_sentence = top_words
        
        logger.info(f"Generated new sentence: {new_sentence}")

        # Load audio snippets for top k words (with caching - do NOT worry ok thanks)
        words_with_audio = { 
            word: disk_io.load_waves_for(word).get_or_else([]) 
            for word in new_sentence 
        }

        # Filter words with no recordings, randomly select one clip per word
        shuffled = [
            random.choice(audios)
            for audios in words_with_audio.values()
            if audios
        ]
        if app_state.run_the_list:
            shuffled = list(words_with_audio.values())
            shuffled = list(itertools.chain.from_iterable(shuffled))

        logger.debug(f"Playable clips: {len(shuffled)}...??")

        if queuing_is_go:
            logger.debug("Waiting for go from silence...")
            queuing_is_go.wait()

        app_state.playback_dirty.clear()

        for audio in shuffled:
            # Stop current playback if should_play is unset during playback
            if not app_state.should_play.is_set():
                logger.debug("Play isn't set anymore, aborting")
                audio_player.stop()
                break

            # Don't stop the playback but stop queuing if the data has been touched
            if app_state.playback_dirty.is_set():
                logger.debug("Playback was dirty, aborting")
                break

            # Block during playback of a single snippet because we don't want to fill our
            # queue with a bunch of audio that is now stale because audio has changed
            logger.info(
                f"playback with settings: attack {app_state.attack}, decay {app_state.decay}, pre_trim {app_state.pre_trim}, post_trim {app_state.post_trim}"
            )
            audio_player.play_blocking(
                audio,
                attack=app_state.attack,
                decay=app_state.decay,
                pre_trim=app_state.pre_trim,
                post_trim=app_state.post_trim
            )
            # Having this queued is critical: We can actually get a new ranking while we're
            # still playing the current audio in this sort of blanking period, so we can
            # have what is hopefully uninterrupted plaback while we update our snippets
            # with the new audio that has been created by the recording thread!
            queuing_is_go = threading.Event()

            silence_duration = app_state.silence_duration
            if app_state.silence_stray:
                silence_duration = silence_duration * random.lognormvariate(0, 0.35)
                if app_state.temperature > 0.6:
                    r = random.random()
                    if r < 0.08:
                        silence_duration *= 0.25  # quick second drip
                    elif r < 0.15:
                        silence_duration *= 2.0   # long buildup
                

            audio_player.queue_silence(silence_duration, queuing_is_go)
    
    logger.info("Playback worker shutting down...")
