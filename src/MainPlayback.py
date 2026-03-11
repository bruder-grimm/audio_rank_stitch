import threading

from pathlib import Path

from audio.DiskIO import DiskIO
from audio.Play import Player
from ranking import Rank
from ranking.RankIO import RankIO
from shuffling.Shuffle import Shuffle
from ui.PlaybackWindow import PlaybackWindow
from util.Logger import LogLevel, Logger

LOGLEVEL = LogLevel.DEBUG

SAMPLING_RATE = 44100
PATH = Path("./../word_snippets")

if __name__ == "__main__":

    # We need to find the top k words
    # For those top k words we get all waves THAT WE DON'T ALREADY HAVE! (in a perfect world)
    # we shuffle the waves (don't forget about the "freshness" of the recordings)
    # we play the files with attack, decay, in-between silence
    # repeat

    logger = Logger(LOGLEVEL)

    rank_io = RankIO(PATH, logger)
    disk_io = DiskIO(PATH, logger, SAMPLING_RATE)

    audio_player = Player(SAMPLING_RATE)

    # Here we go
    app = PlaybackWindow(audio_player, logger)

    def worker():
        while True:
            rankings = rank_io.load_rankings()
            top_words: list[tuple[str, int]] = rankings\
                .map(lambda ranks: Rank.top_k(ranks, 5))\
                .get_or_else([])
            
            word_snippets = { 
                word: disk_io.load_waves_for(word).get_or_else([])
                for word, _ in top_words 
            }

            shuffle = Shuffle(word_snippets, rankings.get_value(), logger)
            top_k = shuffle.get_top_k(app.top_k)
            shuffled = shuffle.shuffle_top_k(top_k, shuffle_factor=0.3)

            if app.play_pressed:
                for audio in shuffled:
                    audio_player.play(audio, attack=app.attack, decay=app.decay)
                    threading.Event().wait(app.silence_duration)
            else:
                threading.Event().wait(3)

            app.set_words(top_words)
            

    threading.Thread(target=worker, daemon=True).start()
    app.mainloop()