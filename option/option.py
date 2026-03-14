from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterator,
    Never,
    assert_never,
    cast,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from ..result import Result

class Option[T]:
    """
    A data type that models a potentially missing value: either `Some(value)` or `Empty()`.

    Use this to model **optional** values without using `None`, and to make potential absence explicit.
    We are able to add structure and reliability to None checks throughout the codebase.
    """

    @staticmethod
    def Some(value: T) -> Option[T]:
        """
        Wrap a present value in an `Option`.

        Use this when you *know* you have a value and want to return an `Option`
        to match a flow that uses `Option` consistently. For the most part the helper functions in
        this class will do this work for you and you should use them instead.

        Args:
            value: The value to wrap.

        Returns:
            An `Option[T]` containing `value`.

        Example:
            opt: Option[int] = Option.Some(123)
        """
        return Some(value)

    @staticmethod
    def Empty() -> Option[T]:
        """
        Return an empty `Option`.

        Use this to represent "no value" explicitly, instead of `None`.
        For the most part we want the helper functions in this class to handle this for you. 
        You shouldn't, in most circumstances, use this in its bare form.

        Returns:
            An empty `Option[T]`.

        Example:
            opt: Option[int] = Option.Empty()
        """
        return cast(Option[T], _EMPTY)

    def IsSome(self) -> bool:
        """
        Check whether this option state is `Some`.
        For use in if statements etc for data flow. Most of the time we want to be using Match,
        that way we are always handling both states this option can be in. Can be used for quick straggly bits of logic.

        Returns:
            *True* if this instance is `Some`, otherwise *False*.

        Example:
            opt: Option[int] = Option.Some(42)
            if opt.IsSome():
                print("Has value")
        """
        return isinstance(self, Some)

    def IsEmpty(self) -> bool:
        """
        Check whether this option state is `Empty`.
        For use in if statements etc for data flow. Most of the time we want to be using Match,
        that way we are always handling both states this option can be in. Can be used for quick straggly bits of logic.

        Returns:
            *True* if this instance is `Empty`, otherwise *False*.

        Example:
            opt: Option[int] = Option.Empty()
            if opt.IsEmpty():
                print("No value")
        """
        return isinstance(self, _Empty)

    def __bool__(self) -> bool:
        """
        Treat `Some` as truthy and `Empty` as falsy. More of a quality of life overload than anything.

        Handy for simple checks, but be careful: it can hide intent in complex logic.

        Example:
            opt: Option[int] = Option.Some(42)
            if opt:
                print("Has value")
        """
        return self.IsSome()

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over the value if present (zero-or-one items).

        This lets you write small patterns like `list(opt)` or comprehensions.
        Prefer `Map`, `Bind` or `Match` for non-trivial logic.

        Example:
            opt: Option[int] = Option.Some(42)
            values = [v for v in opt]

            empty: Option[int] = Option.Empty()
            values = [v for v in empty]
        """
        match self:
            case Some(value=v):
                yield v
            case _Empty():
                return
            case _:
                assert_never(self)

    def __repr__(self) -> str:
        """
        Return a stringified representation of the Option.

        Returns:
            String representation for debugging.

        Example:
            optA: Option[str] = Option.Some("123")
            optB: Option[int] = Option.Empty()

            print(optA)
            print(optB)
        """
        match self:
            case Some(value=v):
                return f"Some({v!r})"
            case _Empty():
                return "Empty()"
            case _:
                assert_never(self)

    def Match[R](self, onSome: Callable[[T], R], onEmpty: Callable[[], R]) -> R:
        """
        Exhaustively handle `Some` and `Empty` and produce an output.

        Use this when you want a single expression that covers both cases and returns
        something.

        Args:
            onSome: Called with the value if present.
            onEmpty: Called if empty.

        Returns:
            The result of either `onSome(value)` or `onEmpty()`.

        Example:
            opt: Option[int] = Option.Some(42)
            text: str = opt.Match(lambda x: str(x), lambda: "missing")
        """
        match self:
            case Some(value=v):
                return onSome(v)
            case _Empty():
                return onEmpty()
            case _:
                assert_never(self)

    def Map[U](self, func: Callable[[T], U]) -> Option[U]:
        """
        Transform the contained value if `Some`.

        Use this for pure transformations where the function returns a normal value.
        If the option is empty, it stays empty. No need to handle `if None` etc

        Args:
            func: Transformation applied to the `Some` value.

        Returns:
            `Some(func(value))` if `Some`, otherwise `Empty()`.

        Example:
            opt: Option[int] = Option.Some(5)
            doubled: Option[int] = opt.Map(lambda x: x*2)
        """
        return self.Match(lambda v: Some(func(v)), Option.Empty)

    def Bind[U](self, func: Callable[[T], Option[U]]) -> Option[U]:
        """
        Chain an option-returning function.

        Use this when the next step may also return an `Option` type and you want to avoid
        nested `Option[Option[int]]` for example.

        Args:
            func: A function that returns an `Option`.

        Returns:
            The result of `func(value)` if present; otherwise `Empty()`.

        Example:
            def ParseInt(input: str) -> Option[int]:
                ...

            opt: Option[str] = Option.Some("123")
            parsed: Option[int] = opt.Bind(ParseInt)
        """
        return self.Match(func, Option.Empty)

    @staticmethod
    def FromNullable(value: T | None) -> Option[T]:
        """
        Safely converts a `T | None` into an `Option[T]`.

        Use this at API boundaries where `None` might appear (like dict.get, library
        calls etc) and you want to get into more explicit optional handling.

        Args:
            value: Possibly-null value.

        Returns:
            `Empty()` if value is None, else `Some(value)`.

        Example:
            data = {"userId": 42}
            userId: Option[int] = Option.FromNullable(data.get("userId"))
            userName: Option[str] = Option.FromNullable(data.get("name"))
        """
        return Option.Empty() if value is None else Some(value)

    @staticmethod
    def FromNullableString(value: str | None, strip: bool = False) -> Option[str]:
        """
        Convert a nullable string into an Option, treating empty strings as absence.

        Use this at text-heavy boundaries (CSV, JSON, form input that kind of thing) where empty or
        whitespace-only strings should be considered "missing".

        Args:
            value: A nullable string input.
            strip: If True, strip whitespace before checking for emptiness.

        Returns:
            Empty() if the value is None or empty (after optional stripping),
            otherwise Some(string).

        Example:
            username: Option: str- = Option.FromNullableString("  alice  ", strip=True)
            empty: Option[str] = Option.FromNullableString("", strip=True)
        """
        if value is None:
            return Option.Empty()

        s = value.strip() if strip else value
        return Option.Empty() if s == "" else Some(s)

    @staticmethod
    def When(predicate: bool, valueFactory: Callable[[], T]) -> Option[T]:
        """
        Conditionally create `Some(...)` based on a predicate.

        Use this when constructing an `Option` is expensive or has side-effects and
        you want to avoid doing it unless the predicate is true.

        Args:
            predicate: Condition to include the value.
            valueFactory: Lazily produces the value.

        Returns:
            `Some(valueFactory())` if predicate is true; otherwise `Empty()`.

        Example:
            isEnabled = True
            opt: Option[int] = Option.When(isEnabled, lambda: 42)
        """
        return Some(valueFactory()) if predicate else Option.Empty()

    @staticmethod
    def Try(func: Callable[[], T], exceptions: Type[BaseException] | tuple[Type[BaseException], ...] = Exception) -> Option[T]:
        """
        Capture exceptions and turn success/failure into `Some/Empty`.

        Use this when absence is an acceptable outcome and you do not want exceptions
        to escape. This is only here to keep boilerplate down. But whenever you are using this function, it should probably be a Result monad you should be using.

        Args:
            func: A callable that may raise an exception.
            exceptions: Exception type(s) to catch (default: Exception).

        Returns:
            `Some(result)` if no exception was raised, otherwise `Empty()`.

        Example:
            opt: Option[int] = Option.Try(lambda: int("123"), ValueError)
            empty: Option[int] = Option.Try(lambda: int("abc"), ValueError)
        """
        try:
            return Some(func())
        except exceptions:
            return Option.Empty()

    def IfEmpty(self, fallback: Callable[[], T]) -> T:
        """
        Extract the value, or compute a fallback if empty.

        Use this when you want a final `T` and you can produce a default lazily.

        Args:
            fallback: Produces a replacement value.

        Returns:
            The contained value if present, else `fallback()`.

        Example:
            opt: Option[int] = Option.Empty()
            value: int = opt.IfEmpty(lambda: GetDefaultValue())
        """
        return self.Match(lambda v: v, fallback)

    def IfEmptyValue(self, fallbackValue: T) -> T:
        """
        Extract the value, or return a provided fallback value.

        Use this when you have a simple constant default.

        Args:
            fallbackValue: Value used when empty.

        Returns:
            The contained value if present, else `fallbackValue`.

        Example:
            opt: Option[int] = Option.Empty()
            value: int = opt.IfEmptyValue(0)
        """
        return self.IfEmpty(lambda: fallbackValue)

    def Unwrap(self) -> T:
        """
        An unsafe extraction of the contained value, raising if empty.

        Use this when emptiness indicates something has gone terribly wrong.
        Good for general debugging.
        Avoid in normal control flow.

        Returns:
            The contained value.

        Raises:
            ValueError: If the option is empty.

        Example:
            opt: Option[int] = Option.Some(42)
            value: int = opt.Unwrap()

            empty: Option[int] = Option.Empty()
            empty.Unwrap() # explodes
        """
        return self.Match(lambda v: v, lambda: (_raise(ValueError("Option is Empty"))))

    def UnwrapOr(self, fallback: Callable[[], T]) -> T:
        """
        Alias for `IfEmpty`: unwrap with a lazy fallback.

        Args:
            fallback: Produces a replacement value.

        Returns:
            The contained value if present, else `fallback()`.

        Example:
            opt: Option[int] = Option.Empty()
            port: int = opt.UnwrapOr(lambda: GetDefault()) 
        """
        return self.IfEmpty(fallback)

    def UnwrapOrValue(self, fallbackValue: T) -> T:
        """
        Alias for `IfEmptyValue`: unwrap with a constant fallback.

        Args:
            fallbackValue: Value used when empty.

        Returns:
            The contained value if present, else `fallbackValue`.

        Example:
            opt: Option[str] = Option.Empty()
            name: str = opt.UnwrapOrValue("unknown")
        """
        return self.IfEmptyValue(fallbackValue)

    def Filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        """
        Keep the value only if it satisfies a predicate.

        `Filter` is for *validation*, not creation. It'll assume you already have an
        `Option` and lets you get rid of values that are Some but not acceptable
        according to whatever the filter is.

        This is especially useful in pipelines where values are:
        - optional,
        - normalised or transformed,
        - then checked against domain constraints.

        If the predicate fails, the `Option` becomes `Empty()` and the rest of the
        pipeline is carries on happily.

        Args:
            predicate: A function that returns True for acceptable values.

        Returns:
            The original `Option` when the value passes the predicate;
            `Empty()` when it does not.

        Example:
            opt: Option[int] = Option.Some(50)
            filtered: Option[int] = opt.Filter(lambda x: x > 100)

            description = (
                Option.FromNullableString("  Hello World  ", strip=True)
                    .Map(lambda s: s.lower())
                    .Filter(lambda s: len(s) <= 20)
            )
        """
        return self.Match(lambda v: Some(v) if predicate(v) else Option.Empty(), Option.Empty)

    def Exists(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check whether a predicate ie a boolean expression holds against the contained value.

        True is there is a value and it meets the criteria of the expression. Empty returns False.

        Args:
            predicate: Expression to test.

        Returns:
            True if `Some(value)` and predicate(value) is True; otherwise False.

        Example:
            opt: Option[int] = Option.Some(150)
            hasLarge: bool = opt.Exists(lambda n: n > 100)
        """
        return self.Match(predicate, lambda: False)

    def ForAll(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check whether a predicate holds for the contained value, and treats an empty as True.

        This is for all values in the option, but treat empty as true because it never broke the rule.

        Args:
            predicate: Condition to test.

        Returns:
            True if empty, else predicate(value).

        Example:
            opt: Option[str] = Option.Some("hello")
            ok: bool = opt.ForAll(lambda s: len(s) < 50)

            empty: Option[str] = Option.Empty()
            ok: bool = empty.ForAll(lambda s: len(s) < 50)
        """
        return self.Match(predicate, lambda: True)

    def Count(self) -> int:
        """
        Count elements in the option (0 or 1).
        Essentially just flips `Empty` to `0` and `Some` to `1`

        Returns:
            1 if `Some`, otherwise 0.

        Example:
            total: Option[int] = Option.Some(42).Count()
            total: Option[int] = Option.Empty().Count()
        """
        return self.Match(lambda _: 1, lambda: 0)

    def Fold[S](self, state: S, folder: Callable[[S, T], S]) -> S:
        """
        Fold the option into an accumulator state.

        Use this when you want to accumulate a result conditionally on Some,
        without having to branch all over the shop.

        Args:
            state: Initial accumulator state.
            folder: Combines (state, value) into a new state.

        Returns:
            `folder(state, value)` if present; otherwise `state`.

        Example:
            opt: Option[int] = Option.Some(10)
            total: int = opt.Fold(5, lambda accumulator, value: accumulator + value)
        """
        return self.Match(lambda v: folder(state, v), lambda: state)

    def Tap(self, action: Callable[[T], None]) -> Option[T]:
        """
        Execute a side-effect on the value if present, returning the original option.

        You can use this for logging, metrics, debugging, saving to disk etc whilst still keeping
        the pipeline fluent.

        Args:
            action: Side-effect executed with the contained value.

        Returns:
            The original option.

        Example:
            opt: Option[int] = Option.Some(42)
            opt.Tap(lambda value: print(f"Got {value}"))
        """
        def _onSome(v: T) -> Option[T]:
            action(v)
            return self
        return self.Match(_onSome, lambda: self)

    def TapEmpty(self, action: Callable[[], None]) -> Option[T]:
        """
        Execute a side-effect if the option is empty, returning the original option.

        You can use this for logging, metrics, debugging, saving to disk etc whilst still keeping
        the pipeline fluent, but only when the value is not present.

        Args:
            action: Side-effect executed when empty.

        Returns:
            The original option.

        Example:
            opt: Option[int] = Option.Empty()
            opt.TapEmpty(lambda: print("Missing value"))
        """
        match self:
            case Some():
                return self
            case _Empty():
                action()
                return self
            case _:
                assert_never(self)

    def OrElse(self, other: Option[T] | Callable[[], Option[T]]) -> Option[T]:
        """
        Provide a fallback option if this one is empty.

        Use this to implement fallback chains.

        Args:
            other: A factory producing a fallback Option[T].

        Returns:
            `self` if it is `Some`, otherwise the fallback option.

        Example:
            first: Option[int] = Option.Empty()
            second: Option[int] = Option.Some(42)
            result: Option[int] = first.OrElse(lambda: second)
        """
        return self if self.IsSome() else other()

    def Zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        """
        Combine two options into one option of a tuple.

        Use this when you need *both* values to proceed. If either is empty, the whole thing is empty.

        Args:
            other: Another option.

        Returns:
            `Some((a, b))` if both are `Some`, otherwise `Empty()`.

        Example:
            optA: Option[int] = Option.Some(1)
            optB: Option[str] = Option.Some("x")
            pair: Option[tuple[int, str]] = optA.Zip(optB)

            optC: Option[int] = Option.Empty()
            pair: Option[tuple[int, int]] = optA.Zip(optC)

            optA: Option[int] = Option.Some(1)
            optB: Option[str] = Option.Some("x")
            optC: Option[float] = Option.Some(1.5)

            pair: Option[tuple[int, str]] = optA.Zip(optB)
            triplet: Option[tuple[tuple[int, str], float]] = pair.Zip(optC)
        """
        return self.Bind(lambda a: other.Map(lambda b: (a, b)))

    def Map2[U, R](self, other: Option[U], func: Callable[[T, U], R]) -> Option[R]:
        """
        A helper function that is extending the zip function.
        Combine two options and map them with a function.

        Use this when you need both values to compute a result, without having to manually zip then mapping.

        Args:
            other: Another option.
            func: Function applied to (value1, value2) when both are present.

        Returns:
            `Some(func(a, b))` if both are `Some`, otherwise `Empty()`.

        Example:
            optA: Option[int] = Option.Some(10)
            optB: Option[int] = Option.Some(5)
            summed = optA.Map2(optB, lambda a, b: a + b)
        """
        return self.Zip(other).Map(lambda t: func(t[0], t[1]))

    @staticmethod
    def All(*options: Option[Any]) -> Option[tuple[Any, ...]]:
        """
        Combine multiple options into an option of one flat tuple.

        Gets you out of spots where you have chained `Zip` calls which produce nested tuples like `(((a, b), c), d)`,
        `All` produces a flat tuple `(a, b, c, d)` that's way easier to work with.

        If any option is `Empty`, the whole result is `Empty`.

        Args:
            *options: Any number of options to combine.

        Returns:
            `Some((v1, v2, v3, ...))` if all are `Some`, otherwise `Empty()`.

        Example:
            config = Option.All(
                GetHost(),
                GetPort(),
                GetTimeout(),
            ).MapN(lambda host, port, timeout: Config(host, port, timeout))
            
            or if they all have the same shape:
            config = Option.All(GetHost(), GetPort(), GetTimeout()).MapN(config)
        """
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
        """
        Transform the contained tuple by unpacking it into the function arguments.

        Use this after `All` to apply a constructor or function that takes multiple arguments.

        Args:
            func: Function to apply with unpacked tuple values as the arguments.

        Returns:
            `Some(func(*values))` if all present otherwise `Empty()`.

        Example:
            config = Option.All(
                GetHost(),
                GetPort(),
                GetTimeout(),
            ).MapN(lambda host, port, timeout: Config(host, port, timeout))
            
            or if they all have the same shape:
            config = Option.All(GetHost(), GetPort(), GetTimeout()).MapN(config)
        """
        return self.Map(lambda t: func(*t))

    def Contains(self, value: T) -> bool:
        """
        Check whether the option contains a specific value.

        Args:
            value: The value to check for.

        Returns:
            True if `Some(v)` and `v == value`, otherwise False.

        Example:
            opt = Option.Some(42)
            opt.Contains(42)
            opt.Contains(99)
        """
        return self.Exists(lambda v: v == value)

    def Flatten(self: Option[Option[T]]) -> Option[T]:
        """
        Flatten a nested `Option[Option[T]]` into `Option[T]`.

        Use this when you accidentally end up with a double-wrapped option.

        Returns:
            The inner option if `Some(inner)`, otherwise `Empty()`.

        Example:
            nested = Option.Some(Option.Some(42))
            flat = nested.Flatten()  # Some(42)

            nestedEmpty = Option.Some(Option.Empty())
            flat = nestedEmpty.Flatten()  # Empty()
        """
        return self.Bind(lambda inner: inner)

    async def MatchAsync[R](self, onSome: Callable[[T], Awaitable[R]], onEmpty: Callable[[], Awaitable[R]]) -> R:
        """
        Async version of `Match`.

        Args:
            onSome: Async handler for the present value.
            onEmpty: Async handler for the empty case.

        Returns:
            Awaited result from the chosen handler.

        Example:
            async def FetchUser(userId: int) -> str:
                return f"User {userId}"

            async def FetchDefault() -> str:
                return "Guest"

            opt: Option[int] = Option.Some(123)
            result = Option[int] await opt.MatchAsync(FetchUser, FetchDefault)
        """
        match self:
            case Some(value=v):
                return await onSome(v)
            case _Empty():
                return await onEmpty()
            case _:
                assert_never(self)

    async def MapAsync[U](self, func: Callable[[T], Awaitable[U]]) -> Option[U]:
        """
        Async version of `Map`.

        Args:
            func: Async transformation applied to the contained value.

        Returns:
            `Some(await func(value))` if present, otherwise `Empty()`.

        Example:
            async def EnrichUser(userId: int) -> str:
                ...

            opt: Option[int] = Option.Some(42)
            enriched: Option[str] = await opt.MapAsync(EnrichUser)
        """
        match self:
            case Some(value=v):
                return Some(await func(v))
            case _Empty():
                return Option.Empty()
            case _:
                assert_never(self)

    async def BindAsync[U](self, func: Callable[[T], Awaitable[Option[U]]]) -> Option[U]:
        """
        Async version of `Bind`.

        Args:
            func: Async function returning an `Option`.

        Returns:
            Awaited `Option` result if present; otherwise `Empty()`.

        Example:
            async def LoadProfile(userId: int) -> Option[str]:
                ...

            opt: Option[int] = Option.Some(42)
            profile: Option[str] = await opt.BindAsync(LoadProfile)
        """
        match self:
            case Some(value=v):
                return await func(v)
            case _Empty():
                return Option.Empty()
            case _:
                assert_never(self)

    def ToResult(self, error: Exception) -> Result[T]:
        """
        Convert an `Option[T]` into a `Result[T]`, using a provided error for `Empty`.

        Use this when absence should become a failure, typically at a boundary where you
        need an error-carrying type rather than an optional.

        Args:
            error: Error used when the option is empty.

        Returns:
            `Result.Success(value)` for `Some(value)`, else `Result.Fail(error)`.

        Example:
            opt = Option.Some(42)
            result = opt.ToResult(ValueError("Not found"))

            empty: Option[int] = Option.Empty()
            result = empty.ToResult(ValueError("Not found"))
        """
        from ..result import Result
        return self.Match(Result.Success, lambda: Result.Fail(error))

def _raise(exc: BaseException) -> Never:
    """
    Raise an exception as an expression.

    This only exists really to make `raise` usable inside lambdas, which is handy in pattern matching implementations.

    Args:
        exc: The exception to raise.

    Raises:
        The provided exception.

    Example:
        opt: Option[int] = Option.Empty()
        value: Option[int] = opt.Match(lambda v: v, lambda: _raise(ValueError("Missing")))
    """
    raise exc

@dataclass(frozen=True, slots=True, repr=False)
class Some(Option[T]):
    """
    Represents the presence of a value in an `Option`.

    Attributes:
        value: The contained value.

    Example:
        opt: Option[int] = Some(10)
        opt.Unwrap()
    """
    value: T

class _Empty(Option[Never]):
    """
    Represents the absence of a value in an `Option`.

    This is a singleton class. Don't instantiate directly - use `Option.Empty()`.

    Example:
        opt: Option[int] = Option.Empty()
        opt.IsEmpty()
    """
    __slots__ = ()
    _instance: _Empty | None = None

    def __new__(cls) -> _Empty:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance


_EMPTY: _Empty = _Empty()
