from __future__ import annotations

from typing import Any, Callable, Iterable

from .option import Option, Some


def Somes(options: Iterable[Option[Any]]) -> list[Any]:
    """
    Extract all `Some` values from an iterable of options, discarding `Empty` entries.

    This is the workhorse for turning a collection of optional results into a clean
    list of values. Equivalent to LanguageExt's `Somes` prelude function.

    Args:
        options: Any iterable of `Option[T]`.

    Returns:
        A list containing only the unwrapped `Some` values, in order.

    Example:
        results = [Option.Some(1), Option.Empty(), Option.Some(3), Option.Empty()]
        values = Somes(results)  # [1, 3]
    """
    return [v for opt in options for v in opt.ToList()]


def Sequence(options: Iterable[Option[Any]]) -> Option[list[Any]]:
    """
    Turn a collection of options into an option of a collection. All or nothing.

    If every option is `Some`, returns `Some(list_of_values)`.
    If any option is `Empty`, the whole result is `Empty`.

    This is the standard functional `sequence` operation. Use it when you need
    *all* values to be present or you want nothing.

    Args:
        options: Any iterable of `Option[T]`.

    Returns:
        `Some(values)` if all are `Some`, otherwise `Empty()`.

    Example:
        all_present = [Option.Some(1), Option.Some(2), Option.Some(3)]
        Sequence(all_present)  # Some([1, 2, 3])

        has_gap = [Option.Some(1), Option.Empty(), Option.Some(3)]
        Sequence(has_gap)  # Empty()
    """
    values: list[Any] = []

    for opt in options:
        if opt.IsEmpty():
            return Option.Empty()
        values.append(opt.Unwrap())

    return Some(values)


def Traverse(items: Iterable[Any], func: Callable[[Any], Option[Any]]) -> Option[list[Any]]:
    """
    Map a function over an iterable and sequence the results. All or nothing.

    This is equivalent to calling `Sequence(map(func, items))` but avoids the
    intermediate list. If any application of `func` produces `Empty`, the whole
    result is `Empty`.

    Args:
        items: Any iterable of input values.
        func: A function that returns an `Option` for each input.

    Returns:
        `Some(mapped_values)` if all applications succeed, otherwise `Empty()`.

    Example:
        def ParseInt(s: str) -> Option[int]:
            return Option.Try(lambda: int(s), ValueError)

        Traverse(["1", "2", "3"], ParseInt)    # Some([1, 2, 3])
        Traverse(["1", "oops", "3"], ParseInt) # Empty()
    """
    values: list[Any] = []

    for item in items:
        result = func(item)
        if result.IsEmpty():
            return Option.Empty()
        values.append(result.Unwrap())

    return Some(values)


def Partition(options: Iterable[Option[Any]]) -> tuple[list[Any], int]:
    """
    Split a collection of options into the extracted values and a count of empties.

    Use this when you want to process whatever values are available while also
    knowing how many were missing.

    Args:
        options: Any iterable of `Option[T]`.

    Returns:
        A tuple of `(values, empty_count)` where `values` is a list of unwrapped
        `Some` values and `empty_count` is the number of `Empty` entries.

    Example:
        results = [Option.Some("a"), Option.Empty(), Option.Some("b"), Option.Empty()]
        values, empties = Partition(results)
        # values == ["a", "b"], empties == 2
    """
    values: list[Any] = []
    empty_count = 0

    for opt in options:
        if opt.IsSome():
            values.append(opt.Unwrap())
        else:
            empty_count += 1

    return values, empty_count


def Choose(items: Iterable[Any], func: Callable[[Any], Option[Any]]) -> list[Any]:
    """
    Apply a function to each item and collect only the `Some` results.

    This is a combination of map and filter in one pass. The function returns
    `Option[U]` for each input, and only the `Some` values are kept.
    Equivalent to LanguageExt's `choose` prelude function.

    Args:
        items: Any iterable of input values.
        func: A function that returns an `Option` for each input.

    Returns:
        A list of unwrapped `Some` values from successful applications.

    Example:
        def TryParsePositive(s: str) -> Option[int]:
            return Option.Try(lambda: int(s), ValueError).Filter(lambda n: n > 0)

        Choose(["1", "-2", "abc", "3"], TryParsePositive)  # [1, 3]
    """
    return Somes(func(item) for item in items)
