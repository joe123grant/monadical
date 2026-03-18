from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any, Never, assert_never, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from ..option import Option
    from ..result import Result


def Rule[T, E](predicate: Callable[[T], bool], error: E) -> Callable[[T], Validation[T, E]]:
    def _rule(value: T) -> Validation[T, E]:
        return Validation.Success(value) if predicate(value) else Validation.Fail([error])
    return _rule


class Validation[T, E]:

    @staticmethod
    def Success(value: T) -> Validation[T, E]:
        return Valid(value)

    @staticmethod
    def Fail(errors: list[E]) -> Validation[Never, E]:
        return Invalid(errors)

    @staticmethod
    def Require(value: T | None, error: E) -> Validation[T, E]:
        return Validation.Fail([error]) if value is None else Validation.Success(value)

    @staticmethod
    def Try(action: Callable[[], T], on_error: Callable[[Exception], list[E]]) -> Validation[T, E]:
        try:
            return Validation.Success(action())
        except Exception as ex:
            return Validation.Fail(on_error(ex))

    @staticmethod
    def Where(rule: Callable[[T], Validation[T, E]]) -> Validator[T, E]:
        return Validator(rule)

    @staticmethod
    def Rule(predicate: Callable[[T], bool], error: E) -> Callable[[T], Validation[T, E]]:
        return Rule(predicate, error)

    def IsOk(self) -> bool:
        return isinstance(self, Valid)

    def HasErrors(self) -> bool:
        return isinstance(self, Invalid)

    def __bool__(self) -> bool:
        return self.IsOk()

    def __iter__(self) -> Iterator[T]:
        match self:
            case Valid(value=v):
                yield v
            case Invalid():
                return
            case _:
                assert_never(self)

    def __repr__(self) -> str:
        match self:
            case Valid(value=v):
                return f"Valid({v!r})"
            case Invalid(errors=e):
                return f"Invalid({e!r})"
            case _:
                assert_never(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Validation):
            return NotImplemented
        match self, other:
            case Valid(value=a), Valid(value=b):
                return a == b
            case Invalid(errors=a), Invalid(errors=b):
                return a == b
            case _:
                return False

    def __hash__(self) -> int:
        match self:
            case Valid(value=v):
                return hash(("Valid", v))
            case Invalid(errors=e):
                return hash(("Invalid", tuple(e)))
            case _:
                assert_never(self)

    def Match[R](self, on_ok: Callable[[T], R], on_error: Callable[[list[E]], R]) -> R:
        match self:
            case Valid(value=v):
                return on_ok(v)
            case Invalid(errors=e):
                return on_error(e)
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Validation[U, E]:
        return self.Match(lambda v: Valid(func(v)), Invalid)

    def MapErrors[E2](self, func: Callable[[E], E2]) -> Validation[T, E2]:
        return self.Match(Valid, lambda errors: Invalid([func(e) for e in errors]))

    def Then[U](self, func: Callable[[T], Validation[U, E]]) -> Validation[U, E]:
        return self.Match(func, Invalid)

    def Catch[E2](self, func: Callable[[list[E]], Validation[T, E2]]) -> Validation[T, E2]:
        return self.Match(Valid, func)

    def Apply[U, R](self, other: Validation[U, E], combiner: Callable[[T, U], R]) -> Validation[R, E]:
        match self, other:
            case Valid(value=a), Valid(value=b):
                return Valid(combiner(a, b))
            case Invalid(errors=a), Invalid(errors=b):
                return Invalid(a + b)
            case Invalid(errors=e), _:
                return Invalid(e)
            case _, Invalid(errors=e):
                return Invalid(e)
            case _:
                assert_never(self)

    def Tap(self, action: Callable[[T], None]) -> Validation[T, E]:
        def _on_ok(v: T) -> Validation[T, E]:
            action(v)
            return self
        return self.Match(_on_ok, lambda _: self)

    def TapErrors(self, action: Callable[[list[E]], None]) -> Validation[T, E]:
        def _on_error(errors: list[E]) -> Validation[T, E]:
            action(errors)
            return self
        return self.Match(lambda _: self, _on_error)

    def Unwrap(self) -> T:
        match self:
            case Valid(value=v):
                return v
            case Invalid(errors=e):
                raise ValueError(f"Validation failed: {e}")
            case _:
                assert_never(self)

    def GetOrElse(self, fallback: Callable[[list[E]], T]) -> T:
        return self.Match(lambda v: v, fallback)

    def GetOr(self, default: T) -> T:
        return self.GetOrElse(lambda _: default)

    def Otherwise(self, other: Validation[T, E]) -> Validation[T, E]:
        match self, other:
            case Valid(), _:
                return self
            case Invalid(), Valid():
                return other
            case Invalid(errors=a), Invalid(errors=b):
                return Invalid(a + b)
            case _:
                assert_never(self)

    def Flatten(self: Validation[Validation[T, E], E]) -> Validation[T, E]:
        return self.Then(lambda inner: inner)

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda _: False)

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        return self.Match(predicate, lambda _: True)

    def ToOption(self) -> Option[T]:
        from ..option import Option
        return self.Match(Option.Some, lambda _: Option.Empty())

    def ToResult(self, error_mapper: Callable[[list[E]], Exception]) -> Result[T]:
        from ..result import Result
        return self.Match(Result.Success, lambda errors: Result.Fail(error_mapper(errors)))

    async def MatchAsync[R](self, on_ok: Callable[[T], Awaitable[R]], on_error: Callable[[list[E]], Awaitable[R]]) -> R:
        match self:
            case Valid(value=v):
                return await on_ok(v)
            case Invalid(errors=e):
                return await on_error(e)
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Validation[U, E]:
        match self:
            case Valid(value=v):
                return Valid(await func(v))
            case Invalid():
                return self
            case _:
                assert_never(self)

    async def ThenAsync[U](self, func: Callable[[T], Awaitable[Validation[U, E]]]) -> Validation[U, E]:
        match self:
            case Valid(value=v):
                return await func(v)
            case Invalid():
                return self
            case _:
                assert_never(self)

    @overload
    def __and__[U](self, other: Validation[U, E]) -> Validation[tuple[T, U], E]: ...

    def __and__(self, other: Any) -> Any:
        return self.Apply(other, lambda a, b: (a, b))


class Validator[T, E]:

    def __init__(self, func: Callable[[T], Validation[T, E]]) -> None:
        self._func = func

    def __call__(self, value: T) -> Validation[T, E]:
        return self._func(value)

    def And(self, rule: Callable[[T], Validation[T, E]]) -> Validator[T, E]:
        def _combined(value: T) -> Validation[T, E]:
            r1 = self._func(value)
            r2 = rule(value)
            match r1, r2:
                case Valid(), Valid():
                    return r1
                case Invalid(errors=e1), Invalid(errors=e2):
                    return Invalid(e1 + e2)
                case Invalid(), _:
                    return r1
                case _, Invalid():
                    return r2
                case _:
                    assert_never(r1)
        return Validator(_combined)

    def Then[U](self, transform: Callable[[T], Validation[U, E]]) -> Validator[U, E]:
        def _combined(value: T) -> Validation[U, E]:
            r1 = self._func(value)
            match r1:
                case Valid(value=v):
                    return transform(v)
                case Invalid():
                    return r1
                case _:
                    assert_never(r1)
        return Validator(_combined)


@dataclass(frozen=True, slots=True, repr=False)
class Valid[T, E](Validation[T, E]):
    value: T


@dataclass(frozen=True, slots=True, repr=False)
class Invalid[E](Validation[Never, E]):
    errors: list[E]
