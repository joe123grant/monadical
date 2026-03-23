from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Never, assert_never, overload

if TYPE_CHECKING:
    from ..option import Option
    from ..result import Result


def Rule[T, E](predicate: Callable[[T], bool], error: E) -> Callable[[T], Validation[T, E]]:
    def _Rule(value: T) -> Validation[T, E]:
        return Validation.Success(value) if predicate(value) else Validation.Fail([error])
    return _Rule


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
    def Try(action: Callable[[], T], onError: Callable[[Exception], list[E]]) -> Validation[T, E]:
        try:
            return Validation.Success(action())
        except Exception as exception:
            return Validation.Fail(onError(exception))

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
            case Valid(value=value):
                yield value
            case Invalid():
                return
            case _:
                assert_never(self)

    def __repr__(self) -> str:
        match self:
            case Valid(value=value):
                return f"Valid({value!r})"
            case Invalid(errors=errors):
                return f"Invalid({errors!r})"
            case _:
                assert_never(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Validation):
            return NotImplemented
        match self, other:
            case Valid(value=left), Valid(value=right):
                return left == right
            case Invalid(errors=left), Invalid(errors=right):
                return left == right
            case _:
                return False

    def __hash__(self) -> int:
        match self:
            case Valid(value=value):
                return hash(("Valid", value))
            case Invalid(errors=errors):
                return hash(("Invalid", tuple(errors)))
            case _:
                assert_never(self)

    def __rshift__[U](self, func: Callable[[T], Validation[U, E]]) -> Validation[U, E]:
        return self.Bind(func)

    @overload
    def __and__[U](self, other: Validation[U, E]) -> Validation[tuple[T, U], E]: ...
    def __and__(self, other: Any) -> Any:
        return self.Apply(other, lambda first, second: (first, second))

    def Match[R](self, onOk: Callable[[T], R], onError: Callable[[list[E]], R]) -> R:
        match self:
            case Valid(value=value):
                return onOk(value)
            case Invalid(errors=errors):
                return onError(errors)
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Validation[U, E]:
        return self.Match(lambda value: Valid(func(value)), Invalid)

    def MapErrors[E2](self, func: Callable[[E], E2]) -> Validation[T, E2]:
        return self.Match(Valid, lambda errors: Invalid([func(error) for error in errors]))

    def Bind[U](self, func: Callable[[T], Validation[U, E]]) -> Validation[U, E]:
        return self.Match(func, Invalid)

    def Then[U](self, func: Callable[[T], Validation[U, E]]) -> Validation[U, E]:
        return self.Bind(func)

    def Catch[E2](self, func: Callable[[list[E]], Validation[T, E2]]) -> Validation[T, E2]:
        return self.Match(Valid, func)

    def Apply[U, R](self, other: Validation[U, E], combiner: Callable[[T, U], R]) -> Validation[R, E]:
        match self, other:
            case Valid(value=leftValue), Valid(value=rightValue):
                return Valid(combiner(leftValue, rightValue))
            case Invalid(errors=leftErrors), Invalid(errors=rightErrors):
                return Invalid(leftErrors + rightErrors)
            case Invalid(errors=errors), _:
                return Invalid(errors)
            case _, Invalid(errors=errors):
                return Invalid(errors)
            case _:
                assert_never(self)

    def Filter(self, predicate: Callable[[T], bool], error: E) -> Validation[T, E]:
        return self.Match(lambda value: self if predicate(value) else Validation.Fail([error]), lambda _: self)

    def Tap(self, action: Callable[[T], None]) -> Validation[T, E]:
        def _OnOk(value: T) -> Validation[T, E]:
            action(value)
            return self
        return self.Match(_OnOk, lambda _: self)

    def TapErrors(self, action: Callable[[list[E]], None]) -> Validation[T, E]:
        def _OnError(errors: list[E]) -> Validation[T, E]:
            action(errors)
            return self
        return self.Match(lambda _: self, _OnError)

    def Unwrap(self) -> T:
        return self.Match(
            lambda value: value,
            lambda errors: (_ for _ in ()).throw(ValueError(f"Validation failed: {errors}"))
        )

    def GetOrElse(self, fallback: Callable[[list[E]], T]) -> T:
        return self.Match(lambda value: value, fallback)

    def GetOr(self, default: T) -> T:
        return self.GetOrElse(lambda _: default)

    def Otherwise(self, other: Validation[T, E]) -> Validation[T, E]:
        match self, other:
            case Valid(), _:
                return self
            case Invalid(), Valid():
                return other
            case Invalid(errors=leftErrors), Invalid(errors=rightErrors):
                return Invalid(leftErrors + rightErrors)
            case _:
                assert_never(self)

    def Flatten(self: Validation[Validation[T, E], E]) -> Validation[T, E]:
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

    def BiFold[S](self, state: S, okFolder: Callable[[S, T], S], errorFolder: Callable[[S, list[E]], S]) -> S:
        return self.Match(lambda value: okFolder(state, value), lambda errors: errorFolder(state, errors))

    def MapN[R](self, func: Callable[..., R]) -> Validation[R, E]:
        return self.Map(lambda values: func(*values))

    def Zip[U](self, other: Validation[U, E]) -> Validation[tuple[T, U], E]:
        return self.Apply(other, lambda first, second: (first, second))

    def Map2[U, R](self, other: Validation[U, E], func: Callable[[T, U], R]) -> Validation[R, E]:
        return self.Apply(other, func)

    def ToList(self) -> list[T]:
        return self.Match(lambda value: [value], lambda _: [])

    def ToNullable(self) -> T | None:
        return self.Match(lambda value: value, lambda _: None)

    def ToOption(self) -> Option[T]:
        from ..option import Option
        return self.Match(Option.Some, lambda _: Option.Empty())

    def ToResult(self, errorMapper: Callable[[list[E]], Exception]) -> Result[T]:
        from ..result import Result
        return self.Match(Result.Success, lambda errors: Result.Fail(errorMapper(errors)))

    async def MatchAsync[R](self, onOk: Callable[[T], Awaitable[R]], onError: Callable[[list[E]], Awaitable[R]]) -> R:
        match self:
            case Valid(value=value):
                return await onOk(value)
            case Invalid(errors=errors):
                return await onError(errors)
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Validation[U, E]:
        match self:
            case Valid(value=value):
                return Valid(await func(value))
            case Invalid():
                return self
            case _:
                assert_never(self)

    async def BindAsync[U](self, func: Callable[[T], Awaitable[Validation[U, E]]]) -> Validation[U, E]:
        match self:
            case Valid(value=value):
                return await func(value)
            case Invalid():
                return self
            case _:
                assert_never(self)


class Validator[T, E]:
    def __init__(self, func: Callable[[T], Validation[T, E]]) -> None:
        self._func = func

    def __call__(self, value: T) -> Validation[T, E]:
        return self._func(value)

    def And(self, rule: Callable[[T], Validation[T, E]]) -> Validator[T, E]:
        def _Combined(value: T) -> Validation[T, E]:
            firstResult = self._func(value)
            secondResult = rule(value)
            match firstResult, secondResult:
                case Valid(), Valid():
                    return firstResult
                case Invalid(errors=firstErrors), Invalid(errors=secondErrors):
                    return Invalid(firstErrors + secondErrors)
                case Invalid(), _:
                    return firstResult
                case _, Invalid():
                    return secondResult
                case _:
                    assert_never(firstResult)
        return Validator(_Combined)

    def Then[U](self, transform: Callable[[T], Validation[U, E]]) -> Validator[U, E]:
        def _Combined(value: T) -> Validation[U, E]:
            firstResult = self._func(value)
            match firstResult:
                case Valid(value=validValue):
                    return transform(validValue)
                case Invalid():
                    return firstResult
                case _:
                    assert_never(firstResult)
        return Validator(_Combined)


@dataclass(frozen=True, slots=True, repr=False)
class Valid[T, E](Validation[T, E]):
    value: T

@dataclass(frozen=True, slots=True, repr=False)
class Invalid[E](Validation[Never, E]):
    errors: list[E]
