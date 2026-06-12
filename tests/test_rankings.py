import pytest

from util.logger import Logger, LogLevel
from ranking.rankings import Rankings
from ranking.embedding import Word


class DummyLogger(Logger):
    def __init__(self):
        super().__init__(level=LogLevel.DEBUG)
        self.messages = []

    def error(self, message: str):
        self.messages.append(("error", message))

    def warn(self, message: str):
        self.messages.append(("warn", message))



def test_rankings_update_and_heapify():
    logger = Logger(level=LogLevel.DEBUG)
    rankings = Rankings(logger)

    assert rankings.is_empty()

    rankings.update([Word("hello", "INTJ"), Word("world", "NOUN")])
    assert not rankings.is_empty()

    rankings.train([[Word("hello", "INTJ")], [Word("hello", "INTJ")]])
    rankings.heapify()

    top_k = rankings.get_top_k_words(2)
    # Keys are Word objects, not strings
    assert any(word.actual_word == "hello" for word in top_k.keys())
    # Values should be sorted in descending order
    assert list(top_k.values())[0] >= list(top_k.values())[1]


def test_rankings_get_words_for_range():
    logger = Logger(level=LogLevel.DEBUG)
    rankings = Rankings(logger)

    rankings.update([Word("cat", "NOUN"), Word("dog", "NOUN"), Word("cat", "NOUN")])
    rankings.heapify()

    selection = rankings.get_words_for_topk_range(0, 1)
    assert len(selection) == 1
    # Keys are Word objects, not strings
    assert any(word.actual_word == "cat" for word in selection.keys())


def test_rankings_deprecation_warning_on_unsorted_access():
    logger = DummyLogger()
    rankings = Rankings(logger)
    rankings.update([Word("cat", "NOUN")])

    # Accessing top-k without heapify should still work but log an error
    result = rankings.get_top_k_words(1)
    assert result
    assert any("Rankings not sorted" in message for level, message in logger.messages)
