from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
import math
import re
from typing import Any
from uuid import UUID

from .result import Result

_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})

def _RequireString(value: str | None, label: str) -> Result[str]:
    if value is None:
        return Result.Fail(ValueError(f"{label}: value is None"))
    stripped = value.strip()
    if not stripped:
        return Result.Fail(ValueError(f"{label}: value is empty"))
    return Result.Success(stripped)

def ParseInt(value: str | None, base: int = 10) -> Result[int]:
    return (
        _RequireString(value, "ParseInt")
        .Bind(lambda text: Result.Try(lambda: int(text, base), lambda exception: ValueError(f"ParseInt: cannot parse {value!r}: {exception}")))
    )

def ParseFloat(value: str | None) -> Result[float]:
    def _Parse(text: str) -> Result[float]:
        return (
            Result.Try(lambda: float(text), lambda exception: ValueError(f"ParseFloat: cannot parse {value!r}: {exception}"))
            .Bind(lambda floatValue: Result.Success(floatValue) if math.isfinite(floatValue) else Result.Fail(ValueError(f"ParseFloat: {value!r} is not finite")))
        )
    return _RequireString(value, "ParseFloat").Bind(_Parse)

def ParseDecimal(value: str | None) -> Result[Decimal]:
    def _Parse(text: str) -> Result[Decimal]:
        return (
            Result.Try(lambda: Decimal(text), lambda exception: ValueError(f"ParseDecimal: cannot parse {value!r}: {exception}"))
            .Bind(lambda decimalValue: Result.Success(decimalValue) if decimalValue.is_finite() else Result.Fail(ValueError(f"ParseDecimal: {value!r} is not finite")))
        )
    return _RequireString(value, "ParseDecimal").Bind(_Parse)

def ParseBool(value: Any, truthy: frozenset[str] = _TRUTHY, falsy: frozenset[str] = _FALSY) -> Result[bool]:
    stringValue = str(value) if value is not None else None
    def _Lookup(text: str) -> Result[bool]:
        lowered = text.lower()
        if lowered in truthy:
            return Result.Success(True)
        if lowered in falsy:
            return Result.Success(False)
        return Result.Fail(ValueError(f"ParseBool: cannot interpret {value!r} as bool"))
    return _RequireString(stringValue, "ParseBool").Bind(_Lookup)

def ParseDate(value: str | None, format: str = "%Y-%m-%d") -> Result[date]:
    return (
        _RequireString(value, "ParseDate")
        .Bind(lambda text: Result.Try(lambda: datetime.strptime(text, format).date(), lambda exception: ValueError(f"ParseDate: cannot parse {value!r} with format {format!r}: {exception}")))
    )

def ParseDatetime(value: str | None, format: str = "%Y-%m-%dT%H:%M:%S") -> Result[datetime]:
    return (
        _RequireString(value, "ParseDatetime")
        .Bind(lambda text: Result.Try(lambda: datetime.strptime(text, format), lambda exception: ValueError(f"ParseDatetime: cannot parse {value!r} with format {format!r}: {exception}")))
    )

def ParseTime(value: str | None, format: str = "%H:%M:%S") -> Result[time]:
    return (
        _RequireString(value, "ParseTime")
        .Bind(lambda text: Result.Try(lambda: datetime.strptime(text, format).time(), lambda exception: ValueError(f"ParseTime: cannot parse {value!r} with format {format!r}: {exception}")))
    )

def ParseUuid(value: str | None) -> Result[UUID]:
    return (
        _RequireString(value, "ParseUuid")
        .Bind(lambda text: Result.Try(lambda: UUID(text), lambda exception: ValueError(f"ParseUuid: cannot parse {value!r}: {exception}")))
    )

def ParseEnum(value: str | None, enumType: type[Enum], caseSensitive: bool = False) -> Result[Enum]:
    def _Lookup(text: str) -> Result[Enum]:
        key = text if caseSensitive else text.upper()
        for member in enumType:
            compare = member.name if caseSensitive else member.name.upper()
            if compare == key:
                return Result.Success(member)
        return Result.Fail(ValueError(f"ParseEnum: {value!r} is not a member of {enumType.__name__}"))
    return _RequireString(value, "ParseEnum").Bind(_Lookup)

def ParseRegex(value: str | None, pattern: str, group: int | str = 0) -> Result[str]:
    def _Match(text: str) -> Result[str]:
        matchResult = re.search(pattern, text)
        if matchResult is None:
            return Result.Fail(ValueError(f"ParseRegex: pattern {pattern!r} did not match {value!r}"))
        return Result.Try(lambda: matchResult.group(group), lambda exception: ValueError(f"ParseRegex: group {group!r} not found: {exception}"))
    return _RequireString(value, "ParseRegex").Bind(_Match)
