from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Never, TypeVar, assert_never, TYPE_CHECKING

if TYPE_CHECKING:
    from ..option import Option

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")


class Result(Generic[T]):
    """
    A data type that models something that can succeed or fail. It exists as either `Success(value)` or `Fail(error)`.

    Use this to model operations that may fail without relying on exceptions for control flow.
    We get explicit, structured error handling, and we can keep pipelines fluent and reliable.

    We would use this structure when an operation might fail, without having to bloat out all of our code with try catches.
    Error handling is explicit rather than dilligence of the dev. 
    """
    @staticmethod
    def Success(value: T) -> Result[T]:
        """
        Wrap a successful value in a `Result`.

        Use this when you *know* you have a successful value and want to return a `Result`
        to match a flow that uses `Result` consistently. For the most part you should use `Try`, `Map`,
        and `Bind` and keep it in a neat pipeline.

        Args:
            value: The successful value to wrap.

        Returns:
            A `Result[T]` representing success.

        Example:
            result = Result.Success(123)
        """

        return Ok(value)

    @staticmethod
    def SuccessNonNull(value: T | None) -> Result[T]:
        """
        Convert a potentially-null value into a `Result`, failing if it is `None`.

        Use this at boundaries where `None` may appear (library returns, dict lookups etc)
        but `None` is not acceptable in your domain.

        Depending on the pipeline this may be more appropriate than an Option

        Args:
            value: A value that may be None.

        Returns:
            `Success(value)` if not None, else `Fail(ValueError(...))`.

        Example:
            userId = Result.SuccessNonNull(row.get("userId"))
        """
        return Result.Fail(ValueError("Value cannot be None")) if value is None else Ok(value)

    @staticmethod
    def Fail(error: Exception) -> Result[Never]:
        """
        Create a failed `Result` with an error.

        Use this to represent a domain or validation failure explicitly, rather than throwing.
        Helper functions like try, match, bind, map should be used rather than calling this explicitly.

        Args:
            error: The exception describing the failure.

        Returns:
            A failed `Result`.

        Example:
            return Result.Fail(ValueError("Invalid postcode"))
        """
        return Failure(error)

    @staticmethod
    def Try(action: Callable[[], T], errorMapper: Callable[[Exception], Exception] = lambda x: x) -> Result[T]:
        """
        Capture exceptions and turn success/failure into `Success/Fail`.

        Use this to keep boilerplate down when calling code that might throw, particularly
        at integration or API boundaries. Inside pure domain logic you should ideally be returning
        `Result` directly rather than throwing.

        Args:
            action: Work to execute.
            errorMapper: Maps the caught exception into the error you want to store.

        Returns:
            `Success(value)` if no exception was raised, otherwise `Fail(mapped_error)`.

        Example:
            parsed = Result.Try(lambda: int(text), errorMapper=lambda ex: ValueError(str(ex)))
        """
        try:
            return Result.Success(action())
        except Exception as ex:
            return Result.Fail(errorMapper(ex))

    def IsSuccess(self) -> bool:
        """
        Check whether this result state is `Success`.

        For use in if-statements etc for data flow. Most of the time we want to be using `Match`,
        that way we are always handling both states this result can be in. Handy for quick
        straggly bits of logic.

        Returns:
            True if this instance is `Success`, otherwise False.
        """
        return isinstance(self, Ok)

    def IsFailure(self) -> bool:
        """
        Check whether this result state is `Fail`.

        For use in if-statements etc for data flow. Most of the time we want to be using `Match`,
        that way we are always handling both states this result can be in. Handy for quick
        straggly bits of logic.

        Returns:
            True if this instance is `Fail`, otherwise False.
        """
        return isinstance(self, Failure)

    def __bool__(self) -> bool:
        """
        Treat `Success` as truthy and `Fail` as falsy. More of a quality of life overload than anything.

        Example:
            if result:
                proceed()
        """
        return self.IsSuccess()

    def Match(self, onSuccess: Callable[[T], R], onFailure: Callable[[Exception], R]) -> R:
        """
        Exhaustively handle `Success` and `Fail` and produce an output.

        Use this when you want a single expression that covers both cases and returns
        something.

        Args:
            onSuccess: Called with the value if the result is successful.
            onFailure: Called with the error if the result is failed.

        Returns:
            The result of either `onSuccess(value)` or `onFailure(error)`.

        Example:
            message = result.Match(lambda v: f"OK: {v}", lambda e: f"Failed: {e}")
        """
        match self:
            case Ok(value=v):
                return onSuccess(v)
            case Failure(error=e):
                return onFailure(e)
            case _:
                assert_never(self)

    def Map(self, func: Callable[[T], U]) -> Result[U]:
        """
        Transform the contained value if `Success`.

        Use this for pure transformations where the function returns a normal value.
        If the result is a failure, it stays a failure. If the mapping throws, it becomes a failure.

        Args:
            func: Transformation applied to the success value.

        Returns:
            `Success(func(value))` if successful, otherwise the original failure.
            If the `func` raises, then it returns `Fail(exception)`.

        Example:
            upper = result.Map(lambda s: s.upper())
        """
        def _onSuccess(v: T) -> Result[U]:
            try:
                return Ok(func(v))
            except Exception as ex:
                return Failure(ex)

        return self.Match(_onSuccess, Failure)

    def Bind(self, func: Callable[[T], Result[U]]) -> Result[U]:
        """
        Chain a result-returning function.

        Use this when the next step may also fail and returns a `Result`.
        This keeps pipelines flat ie it avoids nested `Result[Result[T]]` and preserves errors.

        If the binder throws, that exception becomes a failure.

        Args:
            func: A function that returns a `Result`.

        Returns:
            The result of `func(value)` if successful; otherwise the original failure.
            If `func` raises, returns `Fail(exception)`.

        Example:
            result = read_config().Bind(validate_config).Bind(connect)
        """
        def _onSuccess(v: T) -> Result[U]:
            try:
                return func(v)
            except Exception as ex:
                return Failure(ex)

        return self.Match(_onSuccess, Failure)

    def Tap(self, action: Callable[[T], None]) -> Result[T]:
        """
        Execute a side-effect on the value if successful, returning the original result.

        You can use this for logging, metrics, debugging, saving to disk etc whilst still keeping
        the pipeline fluent. Keep in mind that if your side effect can fail then you should be using TryTap

        Args:
            action: Side-effect executed with the success value.

        Returns:
            The original `Result`.

        Example:
            result.Tap(lambda v: logger.info(f"Loaded {v}"))
        """
        def _onSuccess(v: T) -> Result[T]:
            action(v)
            return self

        return self.Match(_onSuccess, lambda _: self)

    def TryTap(self, action: Callable[[T], None], errorMapper: Callable[[Exception], Exception] = lambda x: x) -> Result[T]:
        """
        Execute a side-effect on success, converting any thrown exception into a failure.

        Use this when the side-effect is not trustworthy and you want failures to be captured rather than exploding out of the pipeline.

        Args:
            action: Side-effect executed with the success value.
            errorMapper: Maps any exception thrown by `action`.

        Returns:
            The original `Result` if the side-effect succeeds; otherwise `Fail(mapped_error)`.

        Example:
            saved = result.TryTap(lambda v: WriteToDisk(v), errorMapper=lambda ex: IOError(str(ex)))
        """
        def _onSuccess(v: T) -> Result[T]:
            try:
                action(v)
                return self
            except Exception as ex:
                return Failure(errorMapper(ex))

        return self.Match(_onSuccess, Failure)

    def TapFail(self, action: Callable[[Exception], None]) -> Result[T]:
        """
        Execute a side-effect if the result is a failure, returning the original result.

        Use this for logging, metrics and debugging while keeping the pipeline fluent.
        This does not catch exceptions from `action` — it will throw.

        If you want side-effects that *cannot* throw out of the pipeline, use `TryTapFail`.

        Args:
            action: Side-effect executed with the error.

        Returns:
            The original `Result`.

        Example:
            result.TapFail(lambda e: logger.warning(f"Failed: {e}"))
        """
        def _onFailure(e: Exception) -> Result[T]:
            action(e)
            return self

        return self.Match(lambda _: self, _onFailure)

    def TryTapFail(self, action: Callable[[Exception], None], errorMapper: Callable[[Exception], Exception] = lambda x: x) -> Result[T]:
        """
        Execute a side-effect on failure, converting any thrown exception into a failure.

        This is the failure-side mirror of `TryTap`.

        Args:
            action: Side-effect executed with the error.
            errorMapper: Maps any exception thrown by `action`.

        Returns:
            The original `Result` if the side-effect succeeds; otherwise `Fail(mapped_error)`.

        Example:
            result = result.TryTapFail(lambda e: Report(e), errorMapper=lambda ex: RuntimeError(str(ex)))
        """
        def _onFailure(e: Exception) -> Result[T]:
            try:
                action(e)
                return self
            except Exception as ex:
                return Failure(errorMapper(ex))

        return self.Match(lambda _: self, _onFailure)

    def IfFail(self, fallback: Callable[[Exception], T]) -> T:
        """
        Extract the success value, or compute a fallback if failed.

        Use this when you want a final `T` and you can produce a default lazily,
        potentially using the error.

        Args:
            fallback: Produces a replacement value given the error.

        Returns:
            The success value if present; otherwise `fallback(error)`.

        Example:
            port = result.IfFail(FetchPortFromConfig)
        """
        return self.Match(lambda v: v, fallback)

    def IfFailValue(self, fallbackValue: T) -> T:
        """
        Extract the success value, or return a provided fallback value.

        Use this when you have a simple constant default.

        Args:
            fallbackValue: Value used when failed.

        Returns:
            The success value if present; otherwise `fallbackValue`.

        Example:
            someName = result.IfFailValue("Jonan the barbarian")
        """
        return self.IfFail(lambda _: fallbackValue)

    def ToOption(self) -> Option[T]:
        """
        Convert a `Result[T]` into an `Option[T]`, discarding the error.

        Use this when you are intentionally stepping down from "I care why it failed"
        to "I only care whether I got a value". This is a destructive way of doing things. Approach with care. 

        Returns:
            `Some(value)` if success, otherwise `Empty()`.

        Example:
            optionalUser = resultUser.ToOption()
        """
        from ..option import Option
        return self.Match(Option.Some, lambda _: Option.Empty())


@dataclass(frozen=True, slots=True)
class Ok(Result[T]):
    """
    Represents a successful computation in a `Result`.

    Attributes:
        value: The successful value.

    Example:
        result = Ok(10)
    """
    value: T


@dataclass(frozen=True, slots=True)
class Failure(Result[Never]):
    """
    Represents a failed computation in a `Result`.

    Attributes:
        error: The error describing the failure.

    Example:
        result = Failure(ValueError("Botched it"))
    """
    error: Exception
