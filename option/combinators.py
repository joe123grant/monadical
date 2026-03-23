from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .option import Option, Some

def Somes(options: Iterable[Option[Any]]) -> list[Any]:
    return [value for option in options for value in option.ToList()]

def Sequence(options: Iterable[Option[Any]]) -> Option[list[Any]]:
    values: list[Any] = []

    for option in options:
        match option:
            case Some(value=value):
                values.append(value)
            case _:
                return Option.Empty()

    return Some(values)

def Traverse(items: Iterable[Any], func: Callable[[Any], Option[Any]]) -> Option[list[Any]]:
    values: list[Any] = []

    for item in items:
        match func(item):
            case Some(value=value):
                values.append(value)
            case _:
                return Option.Empty()

    return Some(values)

def Partition(options: Iterable[Option[Any]]) -> tuple[list[Any], int]:
    values: list[Any] = []
    emptyCount = 0

    for option in options:
        match option:
            case Some(value=value):
                values.append(value)
            case _:
                emptyCount += 1

    return values, emptyCount

def Choose(items: Iterable[Any], func: Callable[[Any], Option[Any]]) -> list[Any]:
    return Somes(func(item) for item in items)
