from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar, cast

T = TypeVar("T")  # success type
E = TypeVar("E", bound=Exception)  # error type


class Result(Generic[T, E]):
    def is_success(self) -> bool:
        return isinstance(self, Success)
    
    def is_failure(self) -> bool:
        return isinstance(self, Failure)
    
    def get_value(self) -> T:
        if self.is_success():
            return self.value  # type: ignore
        else:
            raise ValueError("Cannot get value from a Failure result")
        
    def get_error(self) -> E:
        if self.is_failure():
            return self.error  # type: ignore
        else:
            raise ValueError("Cannot get error from a Success result")
        
    def map[U](self, func: Callable[[T], U]) -> "Result[U, E]":
        if self.is_success():
            try:
                return Success(func(self.get_value()))
            except Exception as e:
                return cast("Result[U, E]", Failure(e))
        else:
            return cast("Result[U, E]", self)  # type: ignore

    def flat_map[U](self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        if self.is_success():
            try:
                return func(self.get_value())
            except Exception as e:
                return cast("Result[U, E]", Failure(e))
        else:
            return cast("Result[U, E]", self)
        
    def get_or_else(self, default: T) -> T:
        if self.is_success():
            return self.get_value()
        else:
            return default
        
    def or_else[X: Exception](self, default: Callable[[], "Result[T, X]"]) -> "Result[T, X]":
        if self.is_success():
            return cast("Result[T, X]", self)
        else:
            return default()
        
    def to_optional(self) -> Optional[T]:
        if self.is_success():
            return self.get_value()
        else:
            return None
        
    def fold[X](self, on_success: Callable[[T], X], on_failure: Callable[[E], X]) -> X:
        if self.is_success():
            return on_success(self.get_value())
        else:
            return on_failure(self.get_error())
        
    def foreach(self, on_success: Callable[[T], None], on_failure: Callable[[E], None]) -> None:
        if self.is_success():
            on_success(self.get_value())
        else:
            on_failure(self.get_error())

    def on_failure(self, func: Callable[[E], None]) -> "Result[T, E]":
        if self.is_failure():
            func(self.get_error())
        return self
    
    def on_success(self, func: Callable[[T], None]) -> "Result[T, E]":
        if self.is_success():
            func(self.get_value())
        return self
        

@dataclass
class Success(Result[T, E]):
    value: T


@dataclass
class Failure(Result[T, E]):
    error: E