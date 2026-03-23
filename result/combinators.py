from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .result import Result, Ok, Failure

def Oks(results: Iterable[Result[Any]]) -> list[Any]:
    values: list[Any] = []
    for result in results:
        result.Match(values.append, lambda _: None)
    return values

def Sequence(results: Iterable[Result[Any]]) -> Result[list[Any]]:
    values: list[Any] = []
    for result in results:
        match result:
            case Ok(value=value):
                values.append(value)
            case Failure():
                return result
            case _:
                return result
    return Result.Success(values)

def Traverse(items: Iterable[Any], func: Callable[[Any], Result[Any]]) -> Result[list[Any]]:
    values: list[Any] = []
    for item in items:
        result = func(item)
        match result:
            case Ok(value=value):
                values.append(value)
            case Failure():
                return result
            case _:
                return result
    return Result.Success(values)

def Partition(results: Iterable[Result[Any]]) -> tuple[list[Any], list[Exception]]:
    values: list[Any] = []
    errors: list[Exception] = []
    for result in results:
        result.Match(values.append, errors.append)
    return values, errors

def Choose(items: Iterable[Any], func: Callable[[Any], Result[Any]]) -> list[Any]:
    return Oks(func(item) for item in items)
