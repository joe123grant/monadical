from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any, Never, assert_never, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from ..option import Option
    from ..result import Result


def Rule[T, E](predicate: Callable[[T], bool], error: E) -> Callable[[T], Validation[T, E]]:
    """Create a validator function from a predicate and a single error value.

    Example:
        is_adult = Rule(lambda n: n >= 18, "Must be 18 or older")
        is_adult(21)  # Valid(21)
        is_adult(16)  # Invalid(["Must be 18 or older"])
    """
    def _rule(value: T) -> Validation[T, E]:
        return Validation.Success(value) if predicate(value) else Validation.Fail([error])
    return _rule


class Validation[T, E]:
    """
    A validation result that is either `Valid(value)` or `Invalid(errors)`.

    Unlike `Result`, failures accumulate — all errors from all failing checks are
    collected rather than stopping at the first one. Build pipelines with
    `Validation.Where(...).And(...).And(...)`.
    """

    # ── Constructors ──────────────────────────────────────────────────────────

    @staticmethod
    def Success(value: T) -> Validation[T, E]:
        """Wrap a value in a successful validation."""
        return Valid(value)

    @staticmethod
    def Fail(errors: list[E]) -> Validation[Never, E]:
        """Create a failed validation with one or more errors."""
        return Invalid(errors)

    @staticmethod
    def Require(value: T | None, error: E) -> Validation[T, E]:
        """Succeed with `value` if it is not None, otherwise fail with `error`.

        Example:
            Validation.Require(row.get("id"), "id is required")
        """
        return Validation.Fail([error]) if value is None else Validation.Success(value)

    @staticmethod
    def Try(action: Callable[[], T], on_error: Callable[[Exception], list[E]]) -> Validation[T, E]:
        """Run `action` and return Success, or catch any exception and map it to errors.

        Example:
            Validation.Try(lambda: int(text), on_error=lambda e: [f"Not a number: {e}"])
        """
        try:
            return Validation.Success(action())
        except Exception as ex:
            return Validation.Fail(on_error(ex))

    @staticmethod
    def Where(rule: Callable[[T], Validation[T, E]]) -> Validator[T, E]:
        """Start a composable validation pipeline.

        Example:
            validate_name = (
                Validation.Where(Rule(lambda s: len(s) >= 2, "Too short"))
                          .And(Rule(lambda s: s.isalpha(), "Letters only"))
            )
            validate_name("Jo")    # Valid("Jo")
            validate_name("J9!")   # Invalid(["Letters only"])
            validate_name("J")     # Invalid(["Too short", "Letters only"])
        """
        return Validator(rule)

    @staticmethod
    def Rule(predicate: Callable[[T], bool], error: E) -> Callable[[T], Validation[T, E]]:
        """Create a validator function from a predicate and a single error value.

        Alias for the module-level `Rule` function — use whichever reads more naturally.
        """
        return Rule(predicate, error)

    # ── State ─────────────────────────────────────────────────────────────────

    def IsOk(self) -> bool:
        """True if this is a `Valid` result."""
        return isinstance(self, Valid)

    def HasErrors(self) -> bool:
        """True if this is an `Invalid` result."""
        return isinstance(self, Invalid)

    def __bool__(self) -> bool:
        return self.IsOk()

    # ── Iteration / repr / equality ───────────────────────────────────────────

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

    # ── Core operations ───────────────────────────────────────────────────────

    def Match[R](self, on_ok: Callable[[T], R], on_error: Callable[[list[E]], R]) -> R:
        """Exhaustively handle both cases and produce a single output value.

        Example:
            message = v.Match(
                on_ok=lambda x: f"Got {x}",
                on_error=lambda errs: "; ".join(errs),
            )
        """
        match self:
            case Valid(value=v):
                return on_ok(v)
            case Invalid(errors=e):
                return on_error(e)
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Validation[U, E]:
        """Transform the valid value. Errors pass through unchanged.

        Example:
            v.Map(str.upper)
        """
        return self.Match(lambda v: Valid(func(v)), Invalid)

    def MapErrors[E2](self, func: Callable[[E], E2]) -> Validation[T, E2]:
        """Transform each error independently. Valid value passes through unchanged.

        Example:
            v.MapErrors(lambda e: {"message": e, "code": "VALIDATION_ERROR"})
        """
        return self.Match(Valid, lambda errors: Invalid([func(e) for e in errors]))

    def Then[U](self, func: Callable[[T], Validation[U, E]]) -> Validation[U, E]:
        """Chain a validation-returning function sequentially.

        Short-circuits on failure — if this is already `Invalid`, `func` is never called.
        Use `Apply` / `&` for parallel error accumulation across independent checks.

        Example:
            parse_int(text).Then(validate_positive)
        """
        return self.Match(func, Invalid)

    def Catch[E2](self, func: Callable[[list[E]], Validation[T, E2]]) -> Validation[T, E2]:
        """Chain a recovery function on the error side.

        `func` receives the full error list and can return a new `Validation` —
        either recovering to `Valid` or transforming the errors.

        Example:
            v.Catch(lambda errs: Valid(default) if recoverable(errs) else Invalid(errs))
        """
        return self.Match(Valid, func)

    def Apply[U, R](self, other: Validation[U, E], combiner: Callable[[T, U], R]) -> Validation[R, E]:
        """Combine two independent validations, accumulating all errors.

        - Both valid   → `Valid(combiner(a, b))`
        - Both invalid → `Invalid(errors_a + errors_b)`
        - One invalid  → that `Invalid`

        Use `&` as shorthand for combining into a tuple.

        Example:
            validated_name.Apply(validated_age, lambda name, age: User(name, age))
        """
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

    # ── Side effects ──────────────────────────────────────────────────────────

    def Tap(self, action: Callable[[T], None]) -> Validation[T, E]:
        """Run a side effect on the valid value and return the original validation unchanged.

        Example:
            v.Tap(lambda x: logger.info(f"Validated: {x}"))
        """
        def _on_ok(v: T) -> Validation[T, E]:
            action(v)
            return self
        return self.Match(_on_ok, lambda _: self)

    def TapErrors(self, action: Callable[[list[E]], None]) -> Validation[T, E]:
        """Run a side effect on the error list and return the original validation unchanged.

        Example:
            v.TapErrors(lambda errs: logger.warning(f"Validation failed: {errs}"))
        """
        def _on_error(errors: list[E]) -> Validation[T, E]:
            action(errors)
            return self
        return self.Match(lambda _: self, _on_error)

    # ── Value extraction ──────────────────────────────────────────────────────

    def Unwrap(self) -> T:
        """Return the valid value, or raise `ValueError` if invalid."""
        match self:
            case Valid(value=v):
                return v
            case Invalid(errors=e):
                raise ValueError(f"Validation failed: {e}")
            case _:
                assert_never(self)

    def GetOrElse(self, fallback: Callable[[list[E]], T]) -> T:
        """Return the valid value, or compute a fallback from the error list.

        Example:
            v.GetOrElse(lambda errs: default_value)
        """
        return self.Match(lambda v: v, fallback)

    def GetOr(self, default: T) -> T:
        """Return the valid value, or a constant default if invalid."""
        return self.GetOrElse(lambda _: default)

    # ── Combining / fallback ──────────────────────────────────────────────────

    def Otherwise(self, other: Validation[T, E]) -> Validation[T, E]:
        """Return self if valid, or fall back to `other`, accumulating errors when both invalid.

        - Valid OR anything         → self
        - Invalid OR Valid          → other
        - Invalid OR Invalid        → Invalid(errors_self + errors_other)

        Example:
            primary.Otherwise(secondary)
        """
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
        """Unwrap a nested `Validation[Validation[T, E], E]` into `Validation[T, E]`."""
        return self.Then(lambda inner: inner)

    # ── Predicates ────────────────────────────────────────────────────────────

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        """True if valid and the value satisfies `predicate`."""
        return self.Match(predicate, lambda _: False)

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        """True if invalid (vacuously), or if valid and the value satisfies `predicate`."""
        return self.Match(predicate, lambda _: True)

    # ── Conversion ────────────────────────────────────────────────────────────

    def ToOption(self) -> Option[T]:
        """Convert to `Option[T]`, silently discarding all errors on failure."""
        from ..option import Option
        return self.Match(Option.Some, lambda _: Option.Empty())

    def ToResult(self, error_mapper: Callable[[list[E]], Exception]) -> Result[T]:
        """Convert to `Result[T]`, collapsing the error list into a single exception.

        Example:
            v.ToResult(lambda errs: ValueError("; ".join(errs)))
        """
        from ..result import Result
        return self.Match(Result.Success, lambda errors: Result.Fail(error_mapper(errors)))

    # ── Async ─────────────────────────────────────────────────────────────────

    async def MatchAsync[R](self, on_ok: Callable[[T], Awaitable[R]], on_error: Callable[[list[E]], Awaitable[R]]) -> R:
        """Async version of `Match`."""
        match self:
            case Valid(value=v):
                return await on_ok(v)
            case Invalid(errors=e):
                return await on_error(e)
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Validation[U, E]:
        """Async version of `Map`."""
        match self:
            case Valid(value=v):
                return Valid(await func(v))
            case Invalid():
                return self  # type: ignore[return-value]
            case _:
                assert_never(self)

    async def ThenAsync[U](self, func: Callable[[T], Awaitable[Validation[U, E]]]) -> Validation[U, E]:
        """Async version of `Then`."""
        match self:
            case Valid(value=v):
                return await func(v)
            case Invalid():
                return self  # type: ignore[return-value]
            case _:
                assert_never(self)

    # ── Operators ─────────────────────────────────────────────────────────────

    @overload
    def __and__[U](self, other: Validation[U, E]) -> Validation[tuple[T, U], E]: ...

    def __and__(self, other: Any) -> Any:
        """Combine two validations into a tuple, accumulating errors. Shorthand for `Apply`.

        Example:
            validated_name & validated_email  # Validation[tuple[str, str], E]
        """
        return self.Apply(other, lambda a, b: (a, b))


class Validator[T, E]:
    """A composable, reusable validation pipeline.

    Build with `Validation.Where(rule).And(rule).Then(transform)` and
    call directly on a value: `validator(value)` returns a `Validation[T, E]`.

    `.And`  — runs both rules on the **same** input and accumulates all errors.
    `.Then` — runs the next step on the **output** of the previous step (short-circuits on failure).

    Example:
        validate_username = (
            Validation.Where(Rule(lambda s: len(s) >= 3, "Too short"))
                      .And(Rule(lambda s: s.isalnum(), "Alphanumeric only"))
                      .And(Rule(lambda s: not s[0].isdigit(), "Cannot start with a digit"))
        )

        parse_and_validate_age = (
            Validation.Where(ParseInt)
                      .Then(Rule(lambda n: n >= 0, "Must be non-negative"))
                      .Then(Rule(lambda n: n <= 120, "Unrealistic age"))
        )
    """

    def __init__(self, func: Callable[[T], Validation[T, E]]) -> None:
        self._func = func

    def __call__(self, value: T) -> Validation[T, E]:
        """Run the pipeline against `value`."""
        return self._func(value)

    def And(self, rule: Callable[[T], Validation[T, E]]) -> Validator[T, E]:
        """Add a parallel rule. Both this and `rule` run on the same input; all errors accumulate.

        Use for independent checks on the same value where you want every failure reported.

        Example:
            Validation.Where(not_empty).And(no_spaces).And(max_length(50))
        """
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
        """Add a sequential step. Receives the output of the previous step; short-circuits on failure.

        Use for dependent steps where each stage feeds into the next, such as parsing
        a raw string into a typed value before running domain checks on that value.

        Example:
            Validation.Where(ParseInt).Then(Rule(lambda n: n > 0, "Must be positive"))
        """
        def _combined(value: T) -> Validation[U, E]:
            r1 = self._func(value)
            match r1:
                case Valid(value=v):
                    return transform(v)
                case Invalid():
                    return r1  # type: ignore[return-value]
                case _:
                    assert_never(r1)
        return Validator(_combined)


@dataclass(frozen=True, slots=True, repr=False)
class Valid[T, E](Validation[T, E]):
    """A successful validation result containing the validated value."""
    value: T


@dataclass(frozen=True, slots=True, repr=False)
class Invalid[E](Validation[Never, E]):
    """A failed validation result containing one or more accumulated errors."""
    errors: list[E]
