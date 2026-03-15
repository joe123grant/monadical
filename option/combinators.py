from __future__ import annotations

from typing import Any, Callable, Iterable

from .option import Option, Some


def Somes(options: Iterable[Option[Any]]) -> list[Any]:
    return [v for opt in options for v in opt.ToList()]

def Sequence(options: Iterable[Option[Any]]) -> Option[list[Any]]:
    values: list[Any] = []

    for opt in options:
        if opt.IsEmpty():
            return Option.Empty()
        values.append(opt.Unwrap())

    return Some(values)

def Traverse(items: Iterable[Any], func: Callable[[Any], Option[Any]]) -> Option[list[Any]]:
    values: list[Any] = []

    for item in items:
        result = func(item)
        if result.IsEmpty():
            return Option.Empty()
        values.append(result.Unwrap())

    return Some(values)

def Partition(options: Iterable[Option[Any]]) -> tuple[list[Any], int]:
    values: list[Any] = []
    empty_count = 0

    for opt in options:
        if opt.IsSome():
            values.append(opt.Unwrap())
        else:
            empty_count += 1

    return values, empty_count

def Choose(items: Iterable[Any], func: Callable[[Any], Option[Any]]) -> list[Any]:
    return Somes(func(item) for item in items)
