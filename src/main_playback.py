import threading

from audio.loading.audio_disk_io import DiskIO
from audio.mixer.audio_mixer import Mixer
from audio.speaker_playback import SpeakerPlayer
from ranking import word_ranking
from ranking.word_ranking_io import RankIO
from shuffling.shuffling import Shuffle
from ui.speaker_playback_server import PlaybackSettingsFrontend
from util.logger import Logger

from config import LOGLEVEL, SAMPLERATE, PATH, PLAYBACK_BLOCKSIZE


if __name__ == "__main__":

    # We need to find the top k words
    # For those top k words we get all waves THAT WE DON'T ALREADY HAVE! (in a perfect world)
    # we shuffle the waves (don't forget about the "freshness" of the recordings)
    # we play the files with attack, decay, in-between silence
    # repeat

    logger = Logger(LOGLEVEL)

    rank_io = RankIO(PATH, logger)
    disk_io = DiskIO(PATH, logger, SAMPLERATE)

    mixer = Mixer()

    audio_player = SpeakerPlayer(mixer, SAMPLERATE)

    # Here we go (again)
    app = PlaybackSettingsFrontend()
    
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=app.run, kwargs={"debug": False}, daemon=True)
    flask_thread.start()
    logger.info("PlaybackSettingsFrontend started on http://localhost:5000")

    def worker():
        while True:
            # Careful: Race conditions may happen: every run through this should make values
            # immutable - that means:
            # deference -> use -> discard
            current_top_k = app.top_k

            # ... should we even load rankings or always generate them?
            # Loaded rankings will always be outdated, unless there was no new audio added
            # How do we detect a change in present audio files?
            rankings = rank_io.load_rankings()\
                .or_else(rank_io.generate_rankings)
            
            if rankings.is_failure():
                logger.debug("Couldn't load or generate rankings, skipping shuffle and playback")
                threading.Event().wait(3)
                continue

            # Okay so we get the top k words
            top_words = word_ranking.top_k(rankings.get_value(), current_top_k)
            app.set_words(top_words)
            
            # Then we get all waves for the top k words...
            word_snippets = { 
                word: disk_io.load_waves_for(word).get_or_else([])
                for word, _ in top_words
            }

            # Then we get the top k words... again? I guess I wanted to do mapping between
            # words and spoken words, but semantically this makes me sick
            shuffle = Shuffle(word_snippets, rankings.get_value(), logger)
            top_k = shuffle.get_top_k(current_top_k)
            shuffled = shuffle.shuffle_top_k(top_k, app.shuffle_factor)

            # all g
            if app.play_pressed:
                for audio in shuffled:
                    audio_player.play(audio, attack=app.attack, decay=app.decay)
                    threading.Event().wait(app.silence_duration)
            else:
                logger.debug("No audio in playback queue")
                threading.Event().wait(3)
            

    threading.Thread(target=worker, daemon=True).start()