from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterator, Never, TypeVar, assert_never, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from ..option import Option
    from ..result import Result

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")
E = TypeVar("E")
E2 = TypeVar("E2")
S = TypeVar("S")


class Validation(Generic[T, E]):
    """
    A data type that models validation that can succeed or fail with *many* errors:
    either `Success(value)` or `Fail(errors)`.

    Use this when you want to accumulate *all* validation issues rather than stopping at the first one.
    That is the entire point of this type: it is explicitly "collect errors" rather than "short-circuit".
    """
    @staticmethod
    def Success(value: T) -> Validation[T, E]:
        """
        Wrap a successful value in a `Validation`.

        Use this when you *know* you have a valid value and want to return a `Validation`
        to match a flow that uses `Validation` consistently. In pipelines you only ever want to use helper functions like apply.

        Args:
            value: The value to wrap.

        Returns:
            A valid `Validation[T, E]`.

        Example:
            v = Validation.Success(123)
        """
        return Valid(value)

    @staticmethod
    def Fail(errors: list[E]) -> Validation[Never, E]:
        """
        Create an invalid `Validation` containing one or more errors.

        Use this to represent validation failure explicitly. Unlike `Result`,
        failures here are expected to be aggregated together rather than just thrown.

        Args:
            errors: A list of validation errors.

        Returns:
            An invalid `Validation`.

        Example:
            return Validation.Fail(["Name is required", "Age must be >= 18"])
        """
        return Invalid(errors)

    @staticmethod
    def SuccessNonNull(value: T | None, error: E) -> Validation[T, E]:
        """
        Convert a potentially-null value into a `Validation`, failing with a provided error if it is `None`.


        Args:
            value: A value that may be None.
            error: Error to emit when value is None.

        Returns:
            `Success(value)` if not None, else `Fail([error])`.

        Example:
            userId = Validation.SuccessNonNull(row.get("userId"), "userId is required")
        """
        return Validation.Fail([error]) if value is None else Validation.Success(value)

    @staticmethod
    def Try(action: Callable[[], T], onException: Callable[[Exception], list[E]]) -> Validation[T, E]:
        """
        Capture exceptions and turn success/failure into `Success/Fail` with *validation errors*.

        Use this to keep boilerplate down at integration boundaries where dodgey third-party code can throw.

        Args:
            action: function to execute.
            onException: Maps a caught exception into a list of validation errors.

        Returns:
            `Success(value)` if no exception was raised, otherwise `Fail(onException(ex))`.

        Example:
            v = Validation.Try(
                lambda: int(text),
                onException=lambda ex: [f"Not a number: {ex}"],
            )
        """
        try:
            return Validation.Success(action())
        except Exception as ex:
            return Validation.Fail(onException(ex))

    def IsValid(self) -> bool:
        """
        Check whether this validation state is `Invalid`.

        For use in if-statements etc for data flow. Most of the time we want to be using `Match`,
        that way we are always handling both states this validation can be in.

        Returns:
            True if this instance is `Invalid`, otherwise False.
        """
        return isinstance(self, Valid)

    def IsInvalid(self) -> bool:
        """
        Check whether this validation state is `Invalid`.

        For use in if-statements etc for data flow. Most of the time we want to be using `Match`,
        that way we are always handling both states this validation can be in.

        Returns:
            True if this instance is `Invalid`, otherwise False.
        """
        return isinstance(self, Invalid)

    def __bool__(self) -> bool:
        """
        Treat `Valid` as truthy and `Invalid` as falsy. More of a quality of life overload than anything.

        Handy for simple checks, but be careful: it can hide intent in complex validation logic.

        Example:
            if validation:
                CarryOnMyWaywardSon()
        """
        return self.IsValid()

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over the value if valid (zero-or-one items).

        This lets you write small patterns like `list(v)` or comprehensions.
        Prefer `Map`, `Bind`, `Apply` or `Match` for non-throwaway logic.

        Example:
            values = [x for x in validation]  # [] or [value]
        """
        match self:
            case Valid(value=v):
                yield v
            case Invalid():
                return
            case _:
                assert_never(self)

    def Match(self, onSuccess: Callable[[T], R], onFailure: Callable[[list[E]], R]) -> R:
        """
        Exhaustively handle `Valid` and `Invalid` and produce an output.

        Use this when you want a single expression that covers both cases and returns
        amsomething.

        Args:
            onSuccess: Called with the value if valid.
            onFailure: Called with the full list of errors if invalid.

        Returns:
            The result of either `onSuccess(value)` or `onFailure(errors)`.

        Example:
            text = v.Match(str, lambda errs: "; ".join(map(str, errs)))
        """
        match self:
            case Valid(value=v):
                return onSuccess(v)
            case Invalid(errors=e):
                return onFailure(e)
            case _:
                assert_never(self)

    def Map(self, func: Callable[[T], U]) -> Validation[U, E]:
        """
        Transform the contained value if `Valid`.

        Use this for pure transformations where the function returns a normal value.

        Args:
            func: Transformation applied to the valid value.

        Returns:
            `Valid(func(value))` if valid; otherwise `Invalid(errors)`.

        Example:
            normalised = v.Map(lambda s: s.strip().lower())
        """
        return self.Match(lambda v: Valid(func(v)), Invalid)

    def MapFail(self, func: Callable[[E], E2]) -> Validation[T, E2]:
        """
        Transform each error if `Invalid`.

        Use this to map from one error representation to another, or to enrich errors
        with context. Each error is transformed independently.

        Args:
            func: Transformation applied to each error.

        Returns:
            The original value if valid, otherwise an invalid validation with mapped errors.

        Example:
            myCodes = v.MapFail(lambda e: Error(code="BAD_INPUT", message=str(e)))
        """
        def _onFailure(errors: list[E]) -> Validation[T, E2]:
            return Invalid([func(e) for e in errors])

        return self.Match(Valid, _onFailure)

    def BiMap(self, onFailure: Callable[[list[E]], list[E2]], onSuccess: Callable[[T], U]) -> Validation[U, E2]:
        """
        Transform either side of the validation.

        Use this when you want to map success and failure in one go:
        - map the successful value, and
        - map the list of errors as a whole.

        Args:
            onFailure: Transforms the full error list.
            onSuccess: Transforms the success value.

        Returns:
            A validation with the mapped value or mapped errors.

        Example:
            v2 = v.BiMap(
                onFailure=lambda errs: [str(e) for e in errs],
                onSuccess=lambda x: x + 1,
            )
        """
        return self.Match(lambda v: Valid(onSuccess(v)), lambda e: Invalid(onFailure(e)))

    def Bind(self, func: Callable[[T], Validation[U, E]]) -> Validation[U, E]:
        """
        Chain a validation-returning function.

        Use this when the next validation step depends on the previous successful value.
        If invalid, errors are preserved and the next step is skipped. This will short circuit your collection of errors.
        This is sequential validation, where apply is parallel styley.

        Args:
            func: A function that returns a `Validation`.

        Returns:
            The result of `func(value)` if valid; otherwise `Invalid(errors)`.

        Example:
            v = parse(payload).Bind(validate_domain_rules)
        """
        return self.Match(func, Invalid)

    def BindFail(self, func: Callable[[list[E]], Validation[T, E2]]) -> Validation[T, E2]:
        """
        Chain a failure-handling validation function.

        Use this when you want to recover from, reinterpret, or enrich a failure state,
        potentially producing a success.

        Args:
            func: Receives the error list and returns a new `Validation`.

        Returns:
            `Valid(value)` if already valid; otherwise the result of `func(errors)`.

        Example:
            recovered = v.BindFail(lambda errs: Valid(default_value) if CanRecover(errs) else Invalid(errs))
        """
        return self.Match(Valid, func)

    def BiBind(self, onFailure: Callable[[list[E]], Validation[U, E2]], onSuccess: Callable[[T], Validation[U, E2]]) -> Validation[U, E2]:
        """
        Chain both sides of the validation.

        Use this when you want to perform a `Bind`-like operation regardless of whether the
        current validation is valid or invalid.

        Args:
            onFailure: Called with errors when invalid.
            onSuccess: Called with the value when valid.

        Returns:
            The result of the chosen binder.

        Example:
            v2 = v.BiBind(
                onFailure=lambda errs: Invalid(NormaliseErrors(errs)),
                onSuccess=lambda x: ValidateMore(x),
            )
        """
        return self.Match(onSuccess, onFailure)

    def Apply(self, other: Validation[U, E], combiner: Callable[[T, U], R]) -> Validation[R, E]:
        """
        Combine two validations, accumulating errors.

        - If both are valid, combine their values.
        - If both are invalid, concatenate their error lists.
        - If one is invalid, return its errors.

        Use this to validate multiple independent fields and get *all* errors back.

        Args:
            other: Another validation.
            combiner: Function applied when both are valid.

        Returns:
            A `Validation` of the combined result, with accumulated errors where applicable.

        Example:
            full = validatedName.Apply(ageValidation, lambda name, age: Person(name=name, age=age))
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

    def Tap(self, action: Callable[[T], None]) -> Validation[T, E]:
        """
        Execute a side-effect on the value if valid, returning the original validation.

        You can use this for logging, metrics, debugging, saving to disk etc whilst still keeping
        the pipeline fluent. This does not catch exceptions from `action` — it will throw.

        Args:
            action: Side-effect executed with the valid value.

        Returns:
            The original `Validation`.

        Example:
            v.Tap(lambda x: logger.info(f"Validated: {x}"))
        """
        def _onSuccess(v: T) -> Validation[T, E]:
            action(v)
            return self

        return self.Match(_onSuccess, lambda _: self)

    def TapFail(self, action: Callable[[list[E]], None]) -> Validation[T, E]:
        """
        Execute a side-effect if invalid, returning the original validation.

        Use this for logging, metrics and debugging while keeping the pipeline fluent.
        This does not catch exceptions from `action` — it will throw.

        Args:
            action: Side-effect executed with the error list.

        Returns:
            The original `Validation`.

        Example:
            v.TapFail(lambda errs: logger.warning(f"Invalid: {errs}"))
        """
        def _onFailure(errors: list[E]) -> Validation[T, E]:
            action(errors)
            return self

        return self.Match(lambda _: self, _onFailure)

    def Fold(self, state: S, folder: Callable[[S, T], S]) -> S:
        """
        Fold the validation into an accumulator state if valid.

        Use this when you want to accumulate a result conditionally on validity,
        without a whole hell of branching.

        Args:
            state: Initial accumulator state.
            folder: Combines (state, value) into a new state.

        Returns:
            `folder(state, value)` if valid; otherwise `state`.

        Example:
            total = v.Fold(total, lambda acc, x: acc + x)
        """
        return self.Match(lambda v: folder(state, v), lambda _: state)

    def BiFold(self, state: S, failFolder: Callable[[S, list[E]], S], succFolder: Callable[[S, T], S]) -> S:
        """
        Fold both sides of the validation into an accumulator.

        Args:
            state: Initial accumulator state.
            failFolder: Combines (state, errors) into a new state when invalid.
            succFolder: Combines (state, value) into a new state when valid.

        Returns:
            The updated accumulator state.

        Example:
            state = v.BiFold(state, AddErrors, AddValue)
        """
        return self.Match(lambda v: succFolder(state, v), lambda e: failFolder(state, e))

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check whether a predicate holds for the contained value, and treats invalid as True.

        This is "for all values in the validation" but for invalid we treat it as true because
        it never broke the rule (there is no value to violate the predicate).

        Args:
            predicate: Condition to test.

        Returns:
            True if invalid, else predicate(value).

        Example:
            ok = v.ForAll(lambda s: len(s) < 50)
        """
        return self.Match(predicate, lambda _: True)

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check whether a predicate holds against the contained value.

        True if there is a valid value and it meets the criteria. Invalid returns False.

        Args:
            predicate: Expression to test.

        Returns:
            True if `Valid(value)` and predicate(value) is True; otherwise False.

        Example:
            hasLarge = v.Exists(lambda n: n > 100)
        """
        return self.Match(predicate, lambda _: False)

    def IfFail(self, fallback: Callable[[list[E]], T]) -> T:
        """
        Extract the value, or compute a fallback if invalid.

        Use this when you want a final `T` and you can produce a default lazily,
        potentially using the error list.

        Args:
            fallback: Produces a replacement value given the errors.

        Returns:
            The contained value if valid; otherwise `fallback(errors)`.

        Example:
            value = v.IfFail(lambda errs: DefaultFromErrors(errs))
        """
        return self.Match(lambda v: v, fallback)

    def IfFailValue(self, fallbackValue: T) -> T:
        """
        Extract the value, or return a provided fallback value.

        Use this when you have a simple constant default.

        Args:
            fallbackValue: Value used when invalid.

        Returns:
            The contained value if valid; otherwise `fallbackValue`.

        Example:
            value = v.IfFailValue("Everything broke")
        """
        return self.IfFail(lambda _: fallbackValue)

    def OrElse(self, other: Validation[T, E]) -> Validation[T, E]:
        """
        Provide a fallback validation, accumulating errors when both are invalid.

        - Valid OR anything -> Valid (keeps the first valid)
        - Invalid OR Valid -> Valid (takes the valid fallback)
        - Invalid OR Invalid -> Invalid(errors_a + errors_b)

        Args:
            other: Fallback validation.

        Returns:
            A validation representing the best available success, or accumulated failures.

        Example:
            v = primary.OrElse(secondary)
        """
        match self, other:
            case Valid(), _:
                return self
            case Invalid(), Valid():
                return other
            case Invalid(errors=a), Invalid(errors=b):
                return Invalid(a + b)
            case Invalid(errors=e), _:
                return Invalid(e)
            case _, Invalid(errors=e):
                return Invalid(e)
            case _:
                assert_never(self)

    def ToOption(self) -> Option[T]:
        """
        Convert a `Validation[T, E]` into an `Option[T]`, discarding all errors.

        Use this when you are intentionally stepping down from "I want all validation errors"
        to "I'm only bothered about the value". This is a destructive function. Here be dragons. 

        Returns:
            `Some(value)` if valid; otherwise `Empty()`.

        Example:
            optionalUser = validatedUser.ToOption()
        """
        from ..option import Option
        return self.Match(Option.Some, lambda _: Option.Empty())

    def ToResult(self, errorMapper: Callable[[list[E]], Exception]) -> Result[T]:
        """
        Convert a `Validation[T, E]` into a `Result[T]`, mapping error lists into a single exception.

        Use this when you are moving from "accumulate errors" into an error-carrying type that models
        a single failure value. The conversion is lossy unless your exception retains the error list.

        This is a destructive function. Use with caution.

        Args:
            errorMapper: Converts the list of errors into an exception.

        Returns:
            `Result.Success(value)` if valid; otherwise `Result.Fail(errorMapper(errors))`.

        Example:
            result = v.ToResult(lambda errs: ValueError("; ".join(map(str, errs))))
        """
        from ..result import Result
        return self.Match(Result.Success, lambda errors: Result.Fail(errorMapper(errors)))

    @overload
    def __and__(self: Validation[T, E], other: Validation[U, E]) -> Validation[tuple[T, U], E]: ...

    def __and__(self, other):
        """
        Combine two validations into a tuple, accumulating errors.

        This is syntactic sugar over `Apply`, returning `(a, b)` when both are valid.

        Example:
            pair = nameValidation & ageValidation
        """
        return self.Apply(other, lambda a, b: (a, b))


@dataclass(frozen=True, slots=True)
class Valid(Validation[T, E]):
    """
    Represents a successful validation in a `Validation`.

    Attributes:
        value: The validated value.

    Example:
        v = Valid(10)
    """
    value: T


@dataclass(frozen=True, slots=True)
class Invalid(Validation[Never, E]):
    """
    Represents a failed validation in a `Validation`.

    Unlike `Result`, an invalid validation carries a *list* of errors to support
    error accumulation.

    Attributes:
        errors: The list of validation errors.

    Example:
        v = Invalid(["Name is required", "Age must be >= 18"])
    """
    errors: list[E]
