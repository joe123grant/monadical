from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
import math
import re
from typing import Any
from uuid import UUID

from .validation import Validation

_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})

def _ValidateString(value: str | None, label: str) -> Validation[str, str]:
    if value is None:
        return Validation.Fail([f"{label}: value is None"])
    stripped = value.strip()
    if not stripped:
        return Validation.Fail([f"{label}: value is empty"])
    return Validation.Success(stripped)

def ParseInt(value: str | None, base: int = 10) -> Validation[int, str]:
    return (
        _ValidateString(value, "ParseInt")
        .Bind(lambda text: Validation.Try(lambda: int(text, base), lambda exception: [f"ParseInt: cannot parse {value!r}: {exception}"]))
    )

def ParseFloat(value: str | None) -> Validation[float, str]:
    def _Parse(text: str) -> Validation[float, str]:
        return (
            Validation.Try(lambda: float(text), lambda exception: [f"ParseFloat: cannot parse {value!r}: {exception}"])
            .Bind(lambda floatValue: Validation.Success(floatValue) if math.isfinite(floatValue) else Validation.Fail([f"ParseFloat: {value!r} is not finite"]))
        )
    return _ValidateString(value, "ParseFloat").Bind(_Parse)

def ParseDecimal(value: str | None) -> Validation[Decimal, str]:
    def _Parse(text: str) -> Validation[Decimal, str]:
        return (
            Validation.Try(lambda: Decimal(text), lambda exception: [f"ParseDecimal: cannot parse {value!r}: {exception}"])
            .Bind(lambda decimalValue: Validation.Success(decimalValue) if decimalValue.is_finite() else Validation.Fail([f"ParseDecimal: {value!r} is not finite"]))
        )
    return _ValidateString(value, "ParseDecimal").Bind(_Parse)

def ParseBool(value: Any, truthy: frozenset[str] = _TRUTHY, falsy: frozenset[str] = _FALSY) -> Validation[bool, str]:
    stringValue = str(value) if value is not None else None
    def _Lookup(text: str) -> Validation[bool, str]:
        lowered = text.lower()
        if lowered in truthy:
            return Validation.Success(True)
        if lowered in falsy:
            return Validation.Success(False)
        return Validation.Fail([f"ParseBool: cannot interpret {value!r} as bool"])
    return _ValidateString(stringValue, "ParseBool").Bind(_Lookup)

def ParseDate(value: str | None, format: str = "%Y-%m-%d") -> Validation[date, str]:
    return (
        _ValidateString(value, "ParseDate")
        .Bind(lambda text: Validation.Try(lambda: datetime.strptime(text, format).date(), lambda exception: [f"ParseDate: cannot parse {value!r} with format {format!r}: {exception}"]))
    )

def ParseDatetime(value: str | None, format: str = "%Y-%m-%dT%H:%M:%S") -> Validation[datetime, str]:
    return (
        _ValidateString(value, "ParseDatetime")
        .Bind(lambda text: Validation.Try(lambda: datetime.strptime(text, format), lambda exception: [f"ParseDatetime: cannot parse {value!r} with format {format!r}: {exception}"]))
    )

def ParseTime(value: str | None, format: str = "%H:%M:%S") -> Validation[time, str]:
    return (
        _ValidateString(value, "ParseTime")
        .Bind(lambda text: Validation.Try(lambda: datetime.strptime(text, format).time(), lambda exception: [f"ParseTime: cannot parse {value!r} with format {format!r}: {exception}"]))
    )

def ParseUuid(value: str | None) -> Validation[UUID, str]:
    return (
        _ValidateString(value, "ParseUuid")
        .Bind(lambda text: Validation.Try(lambda: UUID(text), lambda exception: [f"ParseUuid: cannot parse {value!r}: {exception}"]))
    )

def ParseEnum(value: str | None, enumType: type[Enum], caseSensitive: bool = False) -> Validation[Enum, str]:
    def _Lookup(text: str) -> Validation[Enum, str]:
        key = text if caseSensitive else text.upper()
        for member in enumType:
            compare = member.name if caseSensitive else member.name.upper()
            if compare == key:
                return Validation.Success(member)
        return Validation.Fail([f"ParseEnum: {value!r} is not a member of {enumType.__name__}"])
    return _ValidateString(value, "ParseEnum").Bind(_Lookup)

def ParseRegex(value: str | None, pattern: str, group: int | str = 0) -> Validation[str, str]:
    def _Match(text: str) -> Validation[str, str]:
        matchResult = re.search(pattern, text)
        if matchResult is None:
            return Validation.Fail([f"ParseRegex: pattern {pattern!r} did not match {value!r}"])
        return Validation.Try(lambda: matchResult.group(group), lambda exception: [f"ParseRegex: group {group!r} not found: {exception}"])
    return _ValidateString(value, "ParseRegex").Bind(_Match)
