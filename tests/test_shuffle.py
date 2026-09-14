import random

import numpy as np
from util.logger import Logger, LogLevel
from ranking.shuffling import Shuffle


def test_shuffle_top_k_empty_returns_empty():
    shuffle = Shuffle(Logger(level=LogLevel.DEBUG))
    assert shuffle.shuffle_top_k({}, shuffle_factor=0.5) == []


def test_shuffle_top_k_single_word_returns_same_data():
    shuffle = Shuffle(Logger(level=LogLevel.DEBUG))
    audio = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    result = shuffle.shuffle_top_k({"one": [audio]}, 0.5)
    assert np.array_equal(result[0], audio)


def test_shuffle_top_k_respects_shuffle_factor():
    """Test that shuffle_factor influences the mix of top vs other words."""
    shuffle = Shuffle(Logger(level=LogLevel.DEBUG))
    
    # Create audio segments with distinct values for testing
    top_audios = [np.array([1.0], dtype=np.float32) for _ in range(5)]
    other_audios = [np.array([2.0], dtype=np.float32) for _ in range(5)]
    
    # With shuffle_factor=0.0, should only get top word audio
    result_no_shuffle = shuffle.shuffle_top_k(
        {"top": top_audios, "other": other_audios},
        shuffle_factor=0.0
    )
    assert len(result_no_shuffle) == 5
    assert all(np.array_equal(seg, top_audios[0]) for seg in result_no_shuffle)
    
    # With shuffle_factor=0.5, should get a mix containing both top and other
    random.seed(42)
    result_mixed = shuffle.shuffle_top_k(
        {"top": top_audios, "other": other_audios},
        shuffle_factor=0.5
    )
    # Result should contain both types of audio
    has_top = any(np.array_equal(seg, np.array([1.0], dtype=np.float32)) for seg in result_mixed)
    has_other = any(np.array_equal(seg, np.array([2.0], dtype=np.float32)) for seg in result_mixed)
    assert has_top, "Result should contain top word audio"
    assert has_other, "Result should contain other word audio"
