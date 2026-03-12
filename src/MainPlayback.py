import threading


from audio.DiskIO import DiskIO
from audio.playback_record.Play import Player
from ranking import Rank
from ranking.RankIO import RankIO
from sequencing.Mixer import Mixer
from sequencing.Sequencer import Sequencer
from sequencing.Shuffle import Shuffle
from ui.PlaybackWindow import PlaybackWindow
from util.Logger import Logger

from config import LOGLEVEL, SAMPLERATE, PATH


if __name__ == "__main__":

    # We need to find the top k words
    # For those top k words we get all waves THAT WE DON'T ALREADY HAVE! (in a perfect world)
    # we shuffle the waves (don't forget about the "freshness" of the recordings)
    # we play the files with attack, decay, in-between silence
    # repeat

    logger = Logger(LOGLEVEL)

    rank_io = RankIO(PATH, logger)
    disk_io = DiskIO(PATH, logger, SAMPLERATE)

    audio_player = Player(SAMPLERATE)

    # Here we go (again)
    app = PlaybackWindow(audio_player, logger)


    def worker():
        while True:
            # Careful: Race conditions may happen here since we get modified values from the frontend
            # every run through this should make values as immutable as possible - that means:
            # deference -> use -> discard
            current_top_k = app.top_k

            possible_rankings = rank_io.load_rankings()

            if possible_rankings.is_failure():
                logger.info("Generating new rankings file")
                possible_rankings = rank_io.generate_rankings()
            
            if possible_rankings.is_failure():
                logger.warn("Couldn't generate rankings - no audio files present")
                threading.Event().wait(3)
                continue

            rankings = possible_rankings.get_value()
            
            # save for next run - save a trip to disk
            # Further, this will fail silently if saving was unsuccessful.
            # We can just regenerate, and failing the app over this makes no sense
            rank_io.save_rankings(rankings)

            # Okay so we get the top k words
            top_words = Rank.top_k(rankings, current_top_k)
            app.set_words(top_words)
            
            # Then we get all waves for the top k words... because getting 
            # waves is expensive
            word_snippets = { 
                word: disk_io.load_waves_for(word).get_or_else([])
                for word, _ in top_words
            }

            sequencer = Sequencer(
                logger,
                SAMPLERATE,
                kick_drum   = word_snippets[top_words[0][0]][0],
                snare_drum  = word_snippets[top_words[1][0]][0],
                high_hat    = word_snippets[top_words[2][0]][0],
                toms        = word_snippets[top_words[3][0]][0],
                cymbal      = word_snippets[top_words[4][0]][0],
            )

            sequence_length = 16
            step_length = 0.2

            sequence = sequencer.generate_sequence(sequence_length, step_length)
            mixer = Mixer(SAMPLERATE)

            audio = mixer.mix_down(sequence_length, step_length, sequence)
            audio_player.play(audio, attack=app.attack, decay=app.decay)

            continue

            # Then we get the top k words... again? I guess I wanted to do mapping between
            # words and spoken words, but semantically this makes me sick
            shuffle = Shuffle(word_snippets, rankings, logger)
            top_k = shuffle.get_top_k(current_top_k)
            shuffled = shuffle.shuffle_top_k(top_k, app.shuffle_factor)

            # all g - envelope can be modified while this is playing 
            if app.play_pressed:
                for audio in shuffled:
                    audio_player.play(audio, attack=app.attack, decay=app.decay)
                    threading.Event().wait(app.silence_duration)
            else:
                logger.debug("No audio in playback queue")
                threading.Event().wait(3)
            

    threading.Thread(target=worker, daemon=True).start()
    app.mainloop()