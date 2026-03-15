from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import (
    Any,
    Never,
    assert_never,
    cast,
)

class Option[T]:
    @staticmethod
    def Some(value: T) -> Option[T]:
        return Some(value)

    @staticmethod
    def Empty() -> Option[T]:
        return cast(Option[T], _EMPTY)

    def IsSome(self) -> bool:
        return isinstance(self, Some)

    def IsEmpty(self) -> bool:
        return isinstance(self, _Empty)

    def __bool__(self) -> bool:
        return self.IsSome()

    def __iter__(self) -> Iterator[T]:
        match self:
            case Some(value=v):
                yield v
            case _Empty():
                return
            case _:
                assert_never(self)

    def __repr__(self) -> str:
        match self:
            case Some(value=v):
                return f"Some({v!r})"
            case _Empty():
                return "Empty()"
            case _:
                assert_never(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Option):
            return NotImplemented
        match self, other:
            case Some(value=a), Some(value=b):
                return a == b
            case _Empty(), _Empty():
                return True
            case _:
                return False

    def __hash__(self) -> int:
        match self:
            case Some(value=v):
                return hash(("Some", v))
            case _Empty():
                return hash(("Empty",))
            case _:
                assert_never(self)

    def __or__(self, other: Option[T] | Callable[[], Option[T]]) -> Option[T]:
        if self.IsSome():
            return self
        return other() if callable(other) else other

    def Match[R](self, onSome: Callable[[T], R], onEmpty: Callable[[], R]) -> R:
        match self:
            case Some(value=v):
                return onSome(v)
            case _Empty():
                return onEmpty()
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Option[U]:
        return self.Match(lambda v: Some(func(v)), Option.Empty)

    def BiMap[U](self, onSome: Callable[[T], U], onEmpty: Callable[[], U]) -> Option[U]:
        return self.Match(lambda v: Some(onSome(v)), lambda: Some(onEmpty()))

    def Bind[U](self, func: Callable[[T], Option[U]]) -> Option[U]:
        return self.Match(func, Option.Empty)

    def Filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        return self.Match(lambda v: Some(v) if predicate(v) else Option.Empty(), Option.Empty)

    @staticmethod
    def FromNullable(value: T | None) -> Option[T]:
        return Option.Empty() if value is None else Some(value)

    @staticmethod
    def FromNullableString(value: str | None, strip: bool = False) -> Option[str]:
        if value is None:
            return Option.Empty()

        s = value.strip() if strip else value
        return Option.Empty() if s == "" else Some(s)

    @staticmethod
    def FromDict(data: dict, key: Any) -> Option[Any]:
        return Option.FromNullable(data.get(key))

    @staticmethod
    def FromBool(predicate: bool, value: T) -> Option[T]:
        return Some(value) if predicate else Option.Empty()

    @staticmethod
    def When(predicate: bool, valueFactory: Callable[[], T]) -> Option[T]:
        return Some(valueFactory()) if predicate else Option.Empty()

    @staticmethod
    def Try(func: Callable[[], T], exceptions: type[BaseException] | tuple[type[BaseException], ...] = Exception) -> Option[T]:
        try:
            return Some(func())
        except exceptions:
            return Option.Empty()

    def IfEmpty(self, fallback: Callable[[], T]) -> T:
        return self.Match(lambda v: v, fallback)

    def IfEmptyValue(self, fallbackValue: T) -> T:
        return self.IfEmpty(lambda: fallbackValue)

    def Unwrap(self) -> T:
        return self.Match(lambda v: v, lambda: (_raise(ValueError("Option is Empty"))))

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda: False)

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda: True)

    def Contains(self, value: T) -> bool:
        return self.Exists(lambda v: v == value)

    def Count(self) -> int:
        return self.Match(lambda _: 1, lambda: 0)

    def Fold[S](self, state: S, folder: Callable[[S, T], S]) -> S:
        return self.Match(lambda v: folder(state, v), lambda: state)

    def BiFold[S](self, state: S, someFolder: Callable[[S, T], S], emptyFolder: Callable[[S], S]) -> S:
        return self.Match(lambda v: someFolder(state, v), lambda: emptyFolder(state))

    def Tap(self, action: Callable[[T], None]) -> Option[T]:
        def _onSome(v: T) -> Option[T]:
            action(v)
            return self
        return self.Match(_onSome, lambda: self)

    def TapEmpty(self, action: Callable[[], None]) -> Option[T]:
        match self:
            case Some():
                return self
            case _Empty():
                action()
                return self
            case _:
                assert_never(self)

    def OrElse(self, fallback: Callable[[], Option[T]]) -> Option[T]:
        return self if self.IsSome() else fallback()

    def Zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        return self.Bind(lambda a: other.Map(lambda b: (a, b)))

    def ZipN(self, *others: Option[Any]) -> Option[tuple[Any, ...]]:
        return Option.All(self, *others)

    def Map2[U, R](self, other: Option[U], func: Callable[[T, U], R]) -> Option[R]:
        return self.Zip(other).Map(lambda t: func(t[0], t[1]))

    @staticmethod
    def All(*options: Option[Any]) -> Option[tuple[Any, ...]]:
        if not options:
            return Option.Some(())

        values: list[Any] = []

        for opt in options:
            match opt:
                case Some(value=v):
                    values.append(v)
                case _Empty():
                    return Option.Empty()
                case _:
                    assert_never(opt)

        return Some(tuple(values))

    def MapN[R](self, func: Callable[..., R]) -> Option[R]:
        return self.Map(lambda t: func(*t))

    def Flatten(self: Option[Option[T]]) -> Option[T]:
        return self.Bind(lambda inner: inner)

    def ToList(self) -> list[T]:
        return self.Match(lambda v: [v], lambda: [])

    def ToNullable(self) -> T | None:
        return self.Match(lambda v: v, lambda: None)

    async def MatchAsync[R](self, onSome: Callable[[T], Awaitable[R]], onEmpty: Callable[[], Awaitable[R]]) -> R:
        match self:
            case Some(value=v):
                return await onSome(v)
            case _Empty():
                return await onEmpty()
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Option[U]:
        match self:
            case Some(value=v):
                return Some(await func(v))
            case _Empty():
                return Option.Empty()
            case _:
                assert_never(self)

    async def BindAsync[U](self, func: Callable[[T], Awaitable[Option[U]]]) -> Option[U]:
        match self:
            case Some(value=v):
                return await func(v)
            case _Empty():
                return Option.Empty()
            case _:
                assert_never(self)


def _raise(exc: BaseException) -> Never:
    raise exc

@dataclass(frozen=True, slots=True, repr=False)
class Some[T](Option[T]):
    value: T

class _Empty(Option[Never]):
    __slots__ = ()
    _instance: _Empty | None = None

    def __new__(cls) -> _Empty:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance


_EMPTY: _Empty = _Empty()
