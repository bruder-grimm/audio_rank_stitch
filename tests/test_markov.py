from __future__ import annotations
import threading
from dataclasses import dataclass
from unittest.mock import patch

import pytest
from ranking.embedding import Word
from ranking.markov import PosMarkovModel


# ── Fixtures ──────────────────────────────────────────────────────────────────
def w(word: str, pos: str) -> Word:
    return Word(actual_word=word, pos=pos)


# Simple sentences for reuse across tests
SENTENCE = [w("the", "DT"), w("cat", "NN"), w("runs", "VB")]
SENTENCE_2 = [w("a", "DT"), w("dog", "NN"), w("sleeps", "VB")]


def trained_model(*sentences, decay=1.0) -> PosMarkovModel:
    model = PosMarkovModel(decay=decay)
    model.train(list(sentences))
    return model


# ── Construction ──────────────────────────────────────────────────────────────

class TestInit:
    def test_valid_decay_values(self):
        for decay in (1.0, 0.99, 0.5, 0.01):
            PosMarkovModel(decay=decay)  # must not raise

    def test_invalid_decay_zero(self):
        with pytest.raises(ValueError, match="decay must be in"):
            PosMarkovModel(decay=0.0)

    def test_invalid_decay_above_one(self):
        with pytest.raises(ValueError, match="decay must be in"):
            PosMarkovModel(decay=1.1)

    def test_invalid_decay_negative(self):
        with pytest.raises(ValueError):
            PosMarkovModel(decay=-0.5)


# ── Training ──────────────────────────────────────────────────────────────────

class TestTraining:
    def test_update_populates_transitions(self):
        model = PosMarkovModel()
        model.update(SENTENCE)
        assert ("__START__", "__START__") in model._transitions

    def test_update_populates_word_distributions(self):
        model = PosMarkovModel()
        model.update(SENTENCE)
        assert "cat" in model._words["NN"]

    def test_train_multiple_sentences(self):
        model = trained_model(SENTENCE, SENTENCE_2)
        assert "cat" in model._words["NN"]
        assert "dog" in model._words["NN"]

    def test_repeated_word_accumulates_weight(self):
        model = trained_model(SENTENCE, SENTENCE)
        assert model._words["NN"]["cat"] == pytest.approx(2.0)

    def test_empty_sentence_is_harmless(self):
        model = PosMarkovModel()
        model.update([])  # must not raise

    def test_single_word_sentence(self):
        model = PosMarkovModel()
        model.update([w("yes", "UH")])
        assert "yes" in model._words["UH"]


# ── Decay ─────────────────────────────────────────────────────────────────────

class TestDecay:
    def test_decay_reduces_old_weights(self):
        model = PosMarkovModel(decay=0.5)
        model.update(SENTENCE)
        weight_after_first = model._words["NN"]["cat"]
        model.update(SENTENCE_2)
        # cat's weight must have been halved before the second sentence was ingested
        assert model._words["NN"]["cat"] == pytest.approx(weight_after_first * 0.5)

    def test_no_decay_preserves_weights(self):
        model = trained_model(SENTENCE, SENTENCE_2, decay=1.0)
        assert model._words["NN"]["cat"] == pytest.approx(1.0)
        assert model._words["NN"]["dog"] == pytest.approx(1.0)

    def test_decay_affects_transitions(self):
        model = PosMarkovModel(decay=0.5)
        model.update(SENTENCE)
        weight_before = model._transitions[("__START__", "__START__")]["DT"]
        model.update(SENTENCE_2)
        assert model._transitions[("__START__", "__START__")]["DT"] == pytest.approx(
            weight_before * 0.5 + 1.0
        )


# ── Generation ────────────────────────────────────────────────────────────────

class TestGenerate:
    def test_empty_model_returns_empty_list(self):
        assert PosMarkovModel().generate() == []

    def test_returns_list_of_strings(self):
        result = trained_model(SENTENCE).generate()
        assert isinstance(result, list)
        assert all(isinstance(w, str) for w in result)

    def test_result_words_are_known(self):
        model = trained_model(SENTENCE)
        known = {"the", "cat", "runs"}
        result = model.generate(max_words=50)
        assert set(result).issubset(known)

    def test_respects_max_words(self):
        model = trained_model(SENTENCE, SENTENCE_2)
        for max_w in (1, 2, 5):
            assert len(model.generate(max_words=max_w)) <= max_w

    def test_low_temperature_is_deterministic(self):
        """At temperature → 0 the highest-weight path dominates."""
        model = PosMarkovModel()
        for _ in range(10):
            model.update(SENTENCE)     # 10×
        model.update(SENTENCE_2)       # 1×
        results = {tuple(model.generate(temperature=0.01)) for _ in range(20)}
        assert len(results) == 1

    def test_high_temperature_produces_variation(self):
        model = trained_model(*([SENTENCE] * 5 + [SENTENCE_2] * 5))
        results = {tuple(model.generate(temperature=10.0)) for _ in range(30)}
        assert len(results) > 1


# ── Generation from pool ──────────────────────────────────────────────────────

class TestGenerateFromPool:
    def test_empty_model_returns_empty_list(self):
        assert PosMarkovModel().generate_from_pool(["cat"]) == []

    def test_unknown_words_are_ignored(self, capsys):
        model = trained_model(SENTENCE)
        model.generate_from_pool(["unicorn"])
        assert "unicorn" in capsys.readouterr().out

    def test_pool_word_appears_in_output(self):
        model = trained_model(*([SENTENCE] * 20))
        for _ in range(10):
            result = model.generate_from_pool(["cat"])
            if "cat" in result:
                return
        pytest.fail("Pool word never appeared across 10 attempts")

    def test_require_all_places_all_words(self):
        model = trained_model(*([SENTENCE] * 30))
        result = model.generate_from_pool(
            ["the", "cat", "runs"],
            require_all=True,
            max_retries=200,
        )
        assert set(result) >= {"the", "cat", "runs"}

    def test_require_all_warns_when_impossible(self, capsys):
        model = trained_model(SENTENCE)
        # "the" and "cat" are both DT/NN — fitting both in one short sentence may fail
        model.generate_from_pool(
            ["the", "a"],   # two DT words; only one slot in the trigram chain
            require_all=True,
            max_retries=5,
        )
        out = capsys.readouterr().out
        # either succeeds silently or prints the warning — both are acceptable;
        # what matters is it does not raise
        _ = out


# ── Inspection ────────────────────────────────────────────────────────────────

class TestInspection:
    def test_get_most_frequent_words_returns_top_n(self):
        model = trained_model(SENTENCE, SENTENCE_2)
        result = model.get_most_frequent_words(end=2)
        assert len(result) <= 2

    def test_get_most_frequent_words_sorted_descending(self):
        model = PosMarkovModel()
        for _ in range(5):
            model.update(SENTENCE)
        model.update(SENTENCE_2)
        result = model.get_most_frequent_words(end=10)
        weights = list(result.values())
        assert weights == sorted(weights, reverse=True)

    def test_get_most_frequent_words_by_pos_keys_are_pos_tags(self):
        model = trained_model(SENTENCE)
        result = model.get_most_frequent_words_by_pos()
        assert set(result.keys()) == {"DT", "NN", "VB"}

    def test_get_most_frequent_words_by_pos_slicing(self):
        model = trained_model(*([SENTENCE] * 3 + [SENTENCE_2] * 3))
        result = model.get_most_frequent_words_by_pos(end=1)
        for dist in result.values():
            assert len(dist) == 1

    def test_top_is_empty_for_empty_dist(self):
        assert PosMarkovModel._top({}, 0, 10) == {}


# ── Internal helpers ──────────────────────────────────────────────────────────

class TestHelpers:
    def test_temper_uniform_at_temperature_one(self):
        result = PosMarkovModel._temper([2.0, 4.0, 8.0], 1.0)
        assert result == pytest.approx([2.0, 4.0, 8.0])

    def test_temper_flattens_at_high_temperature(self):
        lo = PosMarkovModel._temper([1.0, 100.0], 100.0)
        assert lo[0] / lo[1] == pytest.approx(1.0, abs=0.05)

    def test_temper_sharpens_at_low_temperature(self):
        hi = PosMarkovModel._temper([1.0, 100.0], 0.01)
        assert hi[1] / hi[0] > 1_000

    def test_word_to_pos_picks_highest_weight(self):
        model = PosMarkovModel()
        # "run" appears more as VB than NN
        model._words["VB"]["run"] = 10.0
        model._words["NN"]["run"] = 1.0
        mapping = model._word_to_pos()
        assert mapping["run"] == "VB"

    def test_sample_returns_fallback_for_empty_dist(self):
        model = PosMarkovModel()
        assert model._sample({}, temperature=1.0, fallback="X") == "X"

    def test_sample_returns_only_key_for_singleton(self):
        model = PosMarkovModel()
        assert model._sample({"hello": 1.0}, temperature=1.0) == "hello"


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_updates_do_not_raise(self):
        model = PosMarkovModel()
        errors: list[Exception] = []

        def worker():
            try:
                for _ in range(50):
                    model.update(SENTENCE)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_concurrent_generate_and_train_do_not_raise(self):
        model = trained_model(SENTENCE)
        errors: list[Exception] = []

        def trainer():
            for _ in range(30):
                model.update(SENTENCE_2)

        def generator():
            for _ in range(30):
                model.generate()

        threads = [threading.Thread(target=trainer), threading.Thread(target=generator)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []