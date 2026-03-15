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
    def Try(action: Callable[[], T], errorMapper: Callable[[Exception], Exception] = lambda x: x) -> Result[T]:
        try:
            return Result.Success(action())
        except Exception as ex:
            return Result.Fail(errorMapper(ex))

    @staticmethod
    def All(*results: Result[Any]) -> Result[tuple[Any, ...]]:
        if not results:
            return Result.Success(())
        values: list[Any] = []
        for r in results:
            match r:
                case Ok(value=v):
                    values.append(v)
                case Failure():
                    return r  # type: ignore[return-value]
                case _:
                    assert_never(r)
        return Result.Success(tuple(values))

    def IsSuccess(self) -> bool:
        return isinstance(self, Ok)

    def IsFailure(self) -> bool:
        return isinstance(self, Failure)

    def __bool__(self) -> bool:
        return self.IsSuccess()

    def __repr__(self) -> str:
        match self:
            case Ok(value=v):
                return f"Ok({v!r})"
            case Failure(error=e):
                return f"Failure({e!r})"
            case _:
                assert_never(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        match self, other:
            case Ok(value=a), Ok(value=b):
                return a == b
            case Failure(error=a), Failure(error=b):
                return type(a) is type(b) and str(a) == str(b)
            case _:
                return False

    def __hash__(self) -> int:
        match self:
            case Ok(value=v):
                return hash(("Ok", v))
            case Failure(error=e):
                return hash(("Failure", type(e), str(e)))
            case _:
                assert_never(self)

    def __iter__(self) -> Iterator[T]:
        match self:
            case Ok(value=v):
                yield v
            case Failure():
                return
            case _:
                assert_never(self)

    def Match[R](self, onSuccess: Callable[[T], R], onFailure: Callable[[Exception], R]) -> R:
        match self:
            case Ok(value=v):
                return onSuccess(v)
            case Failure(error=e):
                return onFailure(e)
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Result[U]:
        def _onSuccess(v: T) -> Result[U]:
            try:
                return Ok(func(v))
            except Exception as ex:
                return Failure(ex)

        return self.Match(_onSuccess, Failure)

    def BiMap[U](self, onSuccess: Callable[[T], U], onFailure: Callable[[Exception], Exception]) -> Result[U]:
        match self:
            case Ok(value=v):
                try:
                    return Ok(onSuccess(v))
                except Exception as ex:
                    return Failure(ex)
            case Failure(error=e):
                return Failure(onFailure(e))
            case _:
                assert_never(self)

    def MapError(self, func: Callable[[Exception], Exception]) -> Result[T]:
        return self.Match(lambda _: self, lambda e: Failure(func(e)))

    def Bind[U](self, func: Callable[[T], Result[U]]) -> Result[U]:
        def _onSuccess(v: T) -> Result[U]:
            try:
                return func(v)
            except Exception as ex:
                return Failure(ex)

        return self.Match(_onSuccess, Failure)

    def Filter(self, predicate: Callable[[T], bool], error: Exception) -> Result[T]:
        return self.Match(lambda v: self if predicate(v) else Result.Fail(error), lambda _: self)

    def OrElse(self, fallback: Callable[[], Result[T]]) -> Result[T]:
        return self if self.IsSuccess() else fallback()

    def Recover(self, func: Callable[[Exception], T]) -> Result[T]:
        return self.Match(lambda _: self, lambda e: Result.Try(lambda: func(e)))

    def RecoverValue(self, value: T) -> Result[T]:
        return self if self.IsSuccess() else Result.Success(value)

    def Tap(self, action: Callable[[T], None]) -> Result[T]:
        def _onSuccess(v: T) -> Result[T]:
            action(v)
            return self

        return self.Match(_onSuccess, lambda _: self)

    def TryTap(self, action: Callable[[T], None], errorMapper: Callable[[Exception], Exception] = lambda x: x) -> Result[T]:
        def _onSuccess(v: T) -> Result[T]:
            try:
                action(v)
                return self
            except Exception as ex:
                return Failure(errorMapper(ex))

        return self.Match(_onSuccess, Failure)

    def TapFail(self, action: Callable[[Exception], None]) -> Result[T]:
        def _onFailure(e: Exception) -> Result[T]:
            action(e)
            return self

        return self.Match(lambda _: self, _onFailure)

    def TryTapFail(self, action: Callable[[Exception], None], errorMapper: Callable[[Exception], Exception] = lambda x: x) -> Result[T]:
        def _onFailure(e: Exception) -> Result[T]:
            try:
                action(e)
                return self
            except Exception as ex:
                return Failure(errorMapper(ex))

        return self.Match(lambda _: self, _onFailure)

    def IfFail(self, fallback: Callable[[Exception], T]) -> T:
        return self.Match(lambda v: v, fallback)

    def IfFailValue(self, fallbackValue: T) -> T:
        return self.IfFail(lambda _: fallbackValue)

    def Zip[U](self, other: Result[U]) -> Result[tuple[T, U]]:
        return self.Bind(lambda a: other.Map(lambda b: (a, b)))

    def ZipN(self, *others: Result[Any]) -> Result[tuple[Any, ...]]:
        return Result.All(self, *others)

    def Map2[U, R](self, other: Result[U], func: Callable[[T, U], R]) -> Result[R]:
        return self.Zip(other).Map(lambda t: func(t[0], t[1]))

    def MapN[R](self, func: Callable[..., R]) -> Result[R]:
        return self.Map(lambda t: func(*t))

    def Flatten(self: Result[Result[T]]) -> Result[T]:
        return self.Bind(lambda inner: inner)

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda _: False)

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda _: True)

    def Contains(self, value: T) -> bool:
        return self.Exists(lambda v: v == value)

    def Count(self) -> int:
        return self.Match(lambda _: 1, lambda _: 0)

    def Fold[S](self, state: S, folder: Callable[[S, T], S]) -> S:
        return self.Match(lambda v: folder(state, v), lambda _: state)

    def BiFold[S](self, state: S, successFolder: Callable[[S, T], S], failureFolder: Callable[[S, Exception], S]) -> S:
        return self.Match(lambda v: successFolder(state, v), lambda e: failureFolder(state, e))

    def ToList(self) -> list[T]:
        return self.Match(lambda v: [v], lambda _: [])

    def ToNullable(self) -> T | None:
        return self.Match(lambda v: v, lambda _: None)

    async def MatchAsync[R](self, onSuccess: Callable[[T], Awaitable[R]], onFailure: Callable[[Exception], Awaitable[R]]) -> R:
        match self:
            case Ok(value=v):
                return await onSuccess(v)
            case Failure(error=e):
                return await onFailure(e)
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Result[U]:
        match self:
            case Ok(value=v):
                return Ok(await func(v))
            case Failure():
                return self  # type: ignore[return-value]
            case _:
                assert_never(self)

    async def BindAsync[U](self, func: Callable[[T], Awaitable[Result[U]]]) -> Result[U]:
        match self:
            case Ok(value=v):
                return await func(v)
            case Failure():
                return self  # type: ignore[return-value]
            case _:
                assert_never(self)


@dataclass(frozen=True, slots=True, repr=False)
class Ok[T](Result[T]):
    value: T


@dataclass(frozen=True, slots=True, repr=False)
class Failure(Result[Never]):
    error: Exception
