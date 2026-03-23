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
    def Try(
        action: Callable[[], T],
        errorMapper: Callable[[Exception], Exception] = lambda exception: exception,
    ) -> Result[T]:
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

    def __hash__(self) -> int:
        match self:
            case Ok(value=value):
                return hash(("Ok", value))
            case Failure(error=error):
                return hash(("Failure", type(error), str(error)))
            case _:
                assert_never(self)

    def __iter__(self) -> Iterator[T]:
        match self:
            case Ok(value=value):
                yield value
            case Failure():
                return
            case _:
                assert_never(self)

    def Match[R](self, onSuccess: Callable[[T], R], onFailure: Callable[[Exception], R]) -> R:
        match self:
            case Ok(value=value):
                return onSuccess(value)
            case Failure(error=error):
                return onFailure(error)
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Result[U]:
        def _OnSuccess(value: T) -> Result[U]:
            try:
                return Ok(func(value))
            except Exception as exception:
                return Failure(exception)
        return self.Match(_OnSuccess, Failure)

    def BiMap[U](
        self, onSuccess: Callable[[T], U], onFailure: Callable[[Exception], Exception]
    ) -> Result[U]:
        match self:
            case Ok(value=value):
                try:
                    return Ok(onSuccess(value))
                except Exception as exception:
                    return Failure(exception)
            case Failure(error=error):
                return Failure(onFailure(error))
            case _:
                assert_never(self)

    def MapError(self, func: Callable[[Exception], Exception]) -> Result[T]:
        return self.Match(lambda _: self, lambda error: Failure(func(error)))

    def Bind[U](self, func: Callable[[T], Result[U]]) -> Result[U]:
        def _OnSuccess(value: T) -> Result[U]:
            try:
                return func(value)
            except Exception as exception:
                return Failure(exception)
        return self.Match(_OnSuccess, Failure)

    def Filter(self, predicate: Callable[[T], bool], error: Exception) -> Result[T]:
        return self.Match(
            lambda value: self if predicate(value) else Result.Fail(error), lambda _: self
        )

    def OrElse(self, fallback: Callable[[], Result[T]]) -> Result[T]:
        return self if self.IsSuccess() else fallback()

    def Recover(self, func: Callable[[Exception], T]) -> Result[T]:
        return self.Match(lambda _: self, lambda error: Result.Try(lambda: func(error)))

    def RecoverValue(self, value: T) -> Result[T]:
        return self if self.IsSuccess() else Result.Success(value)

    def Tap(self, action: Callable[[T], None]) -> Result[T]:
        def _OnSuccess(value: T) -> Result[T]:
            action(value)
            return self
        return self.Match(_OnSuccess, lambda _: self)

    def TryTap(
        self,
        action: Callable[[T], None],
        errorMapper: Callable[[Exception], Exception] = lambda exception: exception,
    ) -> Result[T]:
        def _OnSuccess(value: T) -> Result[T]:
            try:
                action(value)
                return self
            except Exception as exception:
                return Failure(errorMapper(exception))
        return self.Match(_OnSuccess, Failure)

    def TapFail(self, action: Callable[[Exception], None]) -> Result[T]:
        def _OnFailure(error: Exception) -> Result[T]:
            action(error)
            return self
        return self.Match(lambda _: self, _OnFailure)

    def TryTapFail(
        self,
        action: Callable[[Exception], None],
        errorMapper: Callable[[Exception], Exception] = lambda exception: exception,
    ) -> Result[T]:
        def _OnFailure(error: Exception) -> Result[T]:
            try:
                action(error)
                return self
            except Exception as exception:
                return Failure(errorMapper(exception))
        return self.Match(lambda _: self, _OnFailure)

    def IfFail(self, fallback: Callable[[Exception], T]) -> T:
        return self.Match(lambda value: value, fallback)

    def IfFailValue(self, fallbackValue: T) -> T:
        return self.IfFail(lambda _: fallbackValue)

    def Zip[U](self, other: Result[U]) -> Result[tuple[T, U]]:
        return self.Bind(lambda first: other.Map(lambda second: (first, second)))

    def ZipN(self, *others: Result[Any]) -> Result[tuple[Any, ...]]:
        return Result.All(self, *others)

    def Map2[U, R](self, other: Result[U], func: Callable[[T, U], R]) -> Result[R]:
        return self.Zip(other).Map(lambda pair: func(pair[0], pair[1]))

    def MapN[R](self, func: Callable[..., R]) -> Result[R]:
        return self.Map(lambda values: func(*values))

    def Flatten(self: Result[Result[T]]) -> Result[T]:
        return self.Bind(lambda inner: inner)

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda _: False)

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda _: True)

    def Contains(self, value: T) -> bool:
        return self.Exists(lambda current: current == value)

    def Count(self) -> int:
        return self.Match(lambda _: 1, lambda _: 0)

    def Fold[S](self, state: S, folder: Callable[[S, T], S]) -> S:
        return self.Match(lambda value: folder(state, value), lambda _: state)

    def BiFold[S](
        self,
        state: S,
        successFolder: Callable[[S, T], S],
        failureFolder: Callable[[S, Exception], S],
    ) -> S:
        return self.Match(
            lambda value: successFolder(state, value),
            lambda error: failureFolder(state, error),
        )

    def ToList(self) -> list[T]:
        return self.Match(lambda value: [value], lambda _: [])

    def ToNullable(self) -> T | None:
        return self.Match(lambda value: value, lambda _: None)

    async def MatchAsync[R](
        self,
        onSuccess: Callable[[T], Awaitable[R]],
        onFailure: Callable[[Exception], Awaitable[R]],
    ) -> R:
        match self:
            case Ok(value=value):
                return await onSuccess(value)
            case Failure(error=error):
                return await onFailure(error)
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Result[U]:
        match self:
            case Ok(value=value):
                return Ok(await func(value))
            case Failure():
                return self
            case _:
                assert_never(self)

    async def BindAsync[U](self, func: Callable[[T], Awaitable[Result[U]]]) -> Result[U]:
        match self:
            case Ok(value=value):
                return await func(value)
            case Failure():
                return self
            case _:
                assert_never(self)


@dataclass(frozen=True, slots=True, repr=False)
class Ok[T](Result[T]):
    value: T

@dataclass(frozen=True, slots=True, repr=False)
class Failure(Result[Never]):
    error: Exception
