from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any, Never, assert_never


class Result[T]:
    @staticmethod
    def Success(value: T) -> Result[T]:
        return Ok(value)

    @staticmethod
    def SuccessNonNull(value: T | None) -> Result[T]:
        return Result.Fail(ValueError("Value cannot be None")) if value is None else Ok(value)

    @staticmethod
    def Fail(error: Exception) -> Result[Never]:
        return Failure(error)

    @staticmethod
    def Try(action: Callable[[], T], errorMapper: Callable[[Exception], Exception] = lambda exception: exception) -> Result[T]:
        try:
            return Result.Success(action())
        except Exception as exception:
            return Result.Fail(errorMapper(exception))

    @staticmethod
    def All(*results: Result[Any]) -> Result[tuple[Any, ...]]:
        if not results:
            return Result.Success(())
        values: list[Any] = []
        for result in results:
            match result:
                case Ok(value=value):
                    values.append(value)
                case Failure():
                    return result
                case _:
                    assert_never(result)
        return Result.Success(tuple(values))

    def IsSuccess(self) -> bool:
        return isinstance(self, Ok)

    def IsFailure(self) -> bool:
        return isinstance(self, Failure)

    def __bool__(self) -> bool:
        return self.IsSuccess()

    def __or__(self, other: Result[T] | Callable[[], Result[T]]) -> Result[T]:
        if self.IsSuccess():
            return self
        return other() if callable(other) else other

    def __rshift__[U](self, func: Callable[[T], Result[U]]) -> Result[U]:
        return self.Bind(func)

    def __repr__(self) -> str:
        match self:
            case Ok(value=value):
                return f"Ok({value!r})"
            case Failure(error=error):
                return f"Failure({error!r})"
            case _:
                assert_never(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        match self, other:
            case Ok(value=left), Ok(value=right):
                return left == right
            case Failure(error=left), Failure(error=right):
                return type(left) is type(right) and str(left) == str(right)
            case _:
                return False

    def __hash__
