from __future__ import annotations
from typing import Any, Callable, Iterable
from .result import Result

def Oks(results: Iterable[Result[Any]]) -> list[Any]:
    out: list[Any] = []
    for r in results:
        r.Match(out.append, lambda _: None)
    return out

def Sequence(results: Iterable[Result[Any]]) -> Result[list[Any]]:
    values: list[Any] = []
    for r in results:
        if r.IsFailure():
            return r
        r.Match(values.append, lambda _: None)
    return Result.Success(values)

def Traverse(items: Iterable[Any], func: Callable[[Any], Result[Any]]) -> Result[list[Any]]:
    values: list[Any] = []
    for item in items:
        r = func(item)
        if r.IsFailure():
            return r
        r.Match(values.append, lambda _: None)
    return Result.Success(values)

def Partition(results: Iterable[Result[Any]]) -> tuple[list[Any], list[Exception]]:
    values: list[Any] = []
    errors: list[Exception] = []
    for r in results:
        r.Match(values.append, errors.append)
    return values, errors

def Choose(items: Iterable[Any], func: Callable[[Any], Result[Any]]) -> list[Any]:
    return Oks(func(item) for item in items)
