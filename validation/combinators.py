from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .validation import Validation, Valid, Invalid


def Valids(validations: Iterable[Validation[Any, Any]]) -> list[Any]:
    out: list[Any] = []
    for v in validations:
        v.Match(out.append, lambda _: None)
    return out


def Sequence(validations: Iterable[Validation[Any, Any]]) -> Validation[list[Any], Any]:
    values: list[Any] = []
    errors: list[Any] = []

    for v in validations:
        match v:
            case Valid(value=val):
                values.append(val)
            case Invalid(errors=errs):
                errors.extend(errs)

    return Invalid(errors) if errors else Valid(values)


def Traverse(items: Iterable[Any], func: Callable[[Any], Validation[Any, Any]]) -> Validation[list[Any], Any]:
    return Sequence(func(item) for item in items)


def Partition(validations: Iterable[Validation[Any, Any]]) -> tuple[list[Any], list[Any]]:
    values: list[Any] = []
    errors: list[Any] = []

    for v in validations:
        match v:
            case Valid(value=val):
                values.append(val)
            case Invalid(errors=errs):
                errors.extend(errs)

    return values, errors


def Choose(items: Iterable[Any], func: Callable[[Any], Validation[Any, Any]]) -> list[Any]:
    return Valids(func(item) for item in items)
