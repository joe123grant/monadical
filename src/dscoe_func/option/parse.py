from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from enum import Enum
import math
import re
from typing import Any
from uuid import UUID

from .option import Option, Some

_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})

def ParseInt(value: str | None, base: int = 10) -> Option[int]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: int(text, base), ValueError))
    )

def ParseFloat(value: str | None) -> Option[float]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: float(text), ValueError))
        .Filter(math.isfinite)
    )

def ParseDecimal(value: str | None) -> Option[Decimal]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: Decimal(text), InvalidOperation))
        .Filter(lambda decimal: decimal.is_finite())
    )

def ParseBool(value: Any, truthy: frozenset[str] = _TRUTHY, falsy: frozenset[str] = _FALSY) -> Option[bool]:
    return (
        Option.FromNullableString(str(value) if value is not None else None, strip=True)
        .Map(str.lower)
        .Bind(lambda lowered: Option.FromBool(lowered in truthy, True) | Option.FromBool(lowered in falsy, False))
    )

def ParseDate(value: str | None, format: str = "%Y-%m-%d") -> Option[date]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: datetime.strptime(text, format).date(), ValueError))
    )

def ParseDatetime(value: str | None, format: str = "%Y-%m-%dT%H:%M:%S") -> Option[datetime]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: datetime.strptime(text, format), ValueError))
    )

def ParseTime(value: str | None, format: str = "%H:%M:%S") -> Option[time]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: datetime.strptime(text, format).time(), ValueError))
    )

def ParseUuid(value: str | None) -> Option[UUID]:
    return (
        Option.FromNullableString(value, strip=True)
        .Bind(lambda text: Option.Try(lambda: UUID(text), ValueError))
    )

def ParseEnum(value: str | None, enumType: type[Enum], caseSensitive: bool = False) -> Option[Enum]:
    def _Lookup(text: str) -> Option[Enum]:
        key = text if caseSensitive else text.upper()
        for member in enumType:
            compare = member.name if caseSensitive else member.name.upper()
            if compare == key:
                return Some(member)
        return Option.Empty()

    return (
        Option.FromNullableString(value, strip=True)
        .Bind(_Lookup)
    )

def ParseRegex(value: str | None, pattern: str, group: int | str = 0) -> Option[str]:
    return (
        Option.FromNullableString(value)
        .Bind(lambda text: Option.FromNullable(re.search(pattern, text)))
        .Bind(lambda matchResult: Option.Try(lambda: matchResult.group(group), (IndexError, re.error)))
    )
