from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Type
from uuid import UUID

from .option import Option, Some


_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})


def ParseInt(value: str | None, base: int = 10) -> Option[int]:
    return Option.FromNullableString(value, strip=True).Bind(lambda s: Option.Try(lambda: int(s, base), ValueError))

def ParseFloat(value: str | None) -> Option[float]:
    import math
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: float(s), ValueError))
            .Filter(math.isfinite)
    )

def ParseDecimal(value: str | None) -> Option[Decimal]:
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: Decimal(s), InvalidOperation))
            .Filter(lambda d: d.is_finite())
    )


def ParseBool(
    value: str | None,
    truthy: frozenset[str] = _TRUTHY,
    falsy: frozenset[str] = _FALSY,
) -> Option[bool]:
    return (
        Option.FromNullableString(value, strip=True)
            .Map(lambda s: s.lower())
            .Bind(lambda s:
                Some(True) if s in truthy
                else Some(False) if s in falsy
                else Option.Empty()
            )
    )

def ParseDate(value: str | None, fmt: str = "%Y-%m-%d") -> Option[date]:
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: datetime.strptime(s, fmt).date(), ValueError))
    )

def ParseDatetime(value: str | None, fmt: str = "%Y-%m-%dT%H:%M:%S") -> Option[datetime]:
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: datetime.strptime(s, fmt), ValueError))
    )

def ParseTime(value: str | None, fmt: str = "%H:%M:%S") -> Option[time]:
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: datetime.strptime(s, fmt).time(), ValueError))
    )

def ParseUuid(value: str | None) -> Option[UUID]:
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: UUID(s), ValueError))
    )

def ParseEnum(value: str | None, enum_type: Type[Enum], case_sensitive: bool = False) -> Option[Enum]:
    def _lookup(s: str) -> Option[Enum]:
        key = s if case_sensitive else s.upper()
        for member in enum_type:
            compare = member.name if case_sensitive else member.name.upper()
            if compare == key:
                return Some(member)
        return Option.Empty()

    return (
        Option.FromNullableString(value, strip=True)
            .Bind(_lookup)
    )

def ParseRegex(value: str | None, pattern: str, group: int | str = 0) -> Option[str]:
    return (
        Option.FromNullableString(value)
            .Bind(lambda s: Option.FromNullable(re.search(pattern, s)))
            .Bind(lambda m: Option.Try(lambda: m.group(group), (IndexError, re.error)))
    )
