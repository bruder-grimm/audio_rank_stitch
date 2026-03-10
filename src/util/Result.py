from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")  # success type
E = TypeVar("E", bound=Exception)  # error type


class Result(Generic[T, E]):
    pass


@dataclass
class Success(Result[T, E]):
    value: T


@dataclass
class Failure(Result[T, E]):
    error: E