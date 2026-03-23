from __future__ import annotations

from typing import Any, Callable, Iterable

from .validation import Validation, Valid, Invalid

def Valids(validations: Iterable[Validation[Any, Any]]) -> list[Any]:
    values: list[Any] = []
    for validation in validations:
        validation.Match(values.append, lambda _: None)
    return values

def Sequence(validations: Iterable[Validation[Any, Any]]) -> Validation[list[Any], Any]:
    values: list[Any] = []
    errors: list[Any] = []
    for validation in validations:
        match validation:
            case Valid(value=value):
                values.append(value)
            case Invalid(errors=itemErrors):
                errors.extend(itemErrors)
    return Invalid(errors) if errors else Valid(values)

def Traverse(items: Iterable[Any], func: Callable[[Any], Validation[Any, Any]]) -> Validation[list[Any], Any]:
    return Sequence(func(item) for item in items)

def Partition(validations: Iterable[Validation[Any, Any]]) -> tuple[list[Any], list[Any]]:
    values: list[Any] = []
    errors: list[Any] = []
    for validation in validations:
        match validation:
            case Valid(value=value):
                values.append(value)
            case Invalid(errors=itemErrors):
                errors.extend(itemErrors)
    return values, errors

def Choose(items: Iterable[Any], func: Callable[[Any], Validation[Any, Any]]) -> list[Any]:
    return Valids(func(item) for item in items)
