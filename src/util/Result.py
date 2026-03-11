from dataclasses import dataclass
from typing import Generic, TypeVar

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
        
    def map(self, func) -> "Result":
        if self.is_success():
            try:
                return Success(func(self.get_value()))
            except Exception as e:
                return Failure(e)
        else:
            return self  # type: ignore
        
    def get_or_else(self, default: T) -> T:
        if self.is_success():
            return self.get_value()
        else:
            return default
        

@dataclass
class Success(Result[T, E]):
    value: T


@dataclass
class Failure(Result[T, E]):
    error: E