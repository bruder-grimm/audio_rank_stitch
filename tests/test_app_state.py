import json
from pathlib import Path
import tempfile

from app_state import AppState
from ranking.embedding import Word
from ranking.markov import PosMarkovModel
from ranking.rankings import Rankings
from util.logger import Logger, LogLevel


class DummyEmbeddingProvider:
    """Mock embedding provider that doesn't load spaCy."""
    def as_words_with_class(self, tokens: list[str]) -> list[Word]:
        return [Word(token, "NOUN") for token in tokens]


def test_app_state_loads_and_saves_settings(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({
        "attack": 0.2,
        "decay": 0.3,
        "silence_duration": 0.7,
        "shuffle_factor": 0.8,
        "top_k_a": 1,
        "top_k_b": 2,
        "pre_trim": 0.1,
        "post_trim": 0.2,
        "instruction_index": 0,
        "current_instruction": "test",
    }))

    rankings = Rankings(Logger(level=LogLevel.DEBUG))
    model = PosMarkovModel()
    provider = DummyEmbeddingProvider()
    app_state = AppState(rankings, model, provider, settings_path)

    assert app_state.attack == 0.2
    assert app_state.decay == 0.3
    assert app_state.silence_duration == 0.7
    assert app_state.temperature == 0.8
    assert app_state.current_instruction == "test"

    app_state.cycle_instruction()
    assert app_state.get_current_instruction() != "test"

    app_state.shutdown()
    assert settings_path.exists()


def test_app_state_get_current_top_k_selection(tmp_path):
    rankings = Rankings(Logger(level=LogLevel.DEBUG))
    model = PosMarkovModel()
    provider = DummyEmbeddingProvider()
    app_state = AppState(rankings, model, provider, tmp_path / "settings.json")

    model.update([Word("hello", "INTJ"), Word("world", "NOUN")])
    result = app_state.get_current_top_k_selection()
    assert isinstance(result, dict)
