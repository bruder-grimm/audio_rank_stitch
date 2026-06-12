from util.result import Failure, Success


def test_success_and_failure_behaviors():
    value = Success(42)

    assert value.is_success()
    assert not value.is_failure()
    assert value.get_value() == 42
    assert value.to_optional() == 42
    assert value.get_or_else(0) == 42
    assert value.fold(lambda x: x + 1, lambda e: 0) == 43

    mapped = value.map(lambda x: x * 2)
    assert mapped.is_success()
    assert mapped.get_value() == 84

    flat_mapped = value.flat_map(lambda x: Success(str(x)))
    assert flat_mapped.is_success()
    assert flat_mapped.get_value() == "42"

    failure_called = []
    value.foreach(lambda x: failure_called.append(x), lambda _: failure_called.append("failed"))
    assert failure_called == [42]

    assert value.on_success(lambda x: failure_called.append("ok")) is value

    failure_result = Failure(ValueError("boom"))
    assert failure_result.is_failure()
    assert not failure_result.is_success()
    assert failure_result.get_error().args[0] == "boom"
    assert failure_result.get_or_else(0) == 0
    assert failure_result.to_optional() is None

    fallback = failure_result.or_else(lambda: Success(7))
    assert fallback.is_success()
    assert fallback.get_value() == 7

    assert failure_result.fold(lambda x: x, lambda e: e.args[0]) == "boom"

    events = []
    failure_result.foreach(lambda _: events.append("success"), lambda _: events.append("failure"))
    assert events == ["failure"]

    assert failure_result.on_failure(lambda e: events.append(e.args[0])) is failure_result


def test_map_returns_failure_on_exception():
    result = Success(3)

    def raise_error(value):
        raise RuntimeError("bad")

    mapped = result.map(raise_error)
    assert mapped.is_failure()
    assert isinstance(mapped.get_error(), RuntimeError)
