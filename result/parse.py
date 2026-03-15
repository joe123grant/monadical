from __future__ import annotations

import re
import math
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Type
from uuid import UUID

from .result import Result

_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})


def _require_string(value: str | None, label: str) -> Result[str]:
    if value is None:
        return Result.Fail(ValueError(f"{label}: value is None"))
    s = value.strip()
    if not s:
        return Result.Fail(ValueError(f"{label}: value is empty"))
    return Result.Success(s)


def ParseInt(value: str | None, base: int = 10) -> Result[int]:
    return (
        _require_string(value, "ParseInt")
        .Bind(lambda s: Result.Try(lambda: int(s, base), lambda e: ValueError(f"ParseInt: cannot parse {value!r}: {e}")))
    )

def ParseFloat(value: str | None) -> Result[float]:
    def _parse(s: str) -> Result[float]:
        return (
            Result.Try(lambda: float(s), lambda e: ValueError(f"ParseFloat: cannot parse {value!r}: {e}"))
            .Bind(lambda f: Result.Success(f) if math.isfinite(f) else Result.Fail(ValueError(f"ParseFloat: {value!r} is not finite")))
        )
    return _require_string(value, "ParseFloat").Bind(_parse)

def ParseDecimal(value: str | None) -> Result[Decimal]:
    def _parse(s: str) -> Result[Decimal]:
        return (
            Result.Try(lambda: Decimal(s), lambda e: ValueError(f"ParseDecimal: cannot parse {value!r}: {e}"))
            .Bind(lambda d: Result.Success(d) if d.is_finite() else Result.Fail(ValueError(f"ParseDecimal: {value!r} is not finite")))
        )
    return _require_string(value, "ParseDecimal").Bind(_parse)

def ParseBool(value: Any, truthy: frozenset[str] = _TRUTHY, falsy: frozenset[str] = _FALSY) -> Result[bool]:
    str_val = str(value) if value is not None else None

    def _lookup(s: str) -> Result[bool]:
        lower = s.lower()
        if lower in truthy:
            return Result.Success(True)
        if lower in falsy:
            return Result.Success(False)
        return Result.Fail(ValueError(f"ParseBool: cannot interpret {value!r} as bool"))

    return _require_string(str_val, "ParseBool").Bind(_lookup)

def ParseDate(value: str | None, fmt: str = "%Y-%m-%d") -> Result[date]:
    return (
        _require_string(value, "ParseDate")
        .Bind(lambda s: Result.Try(lambda: datetime.strptime(s, fmt).date(), lambda e: ValueError(f"ParseDate: cannot parse {value!r} with format {fmt!r}: {e}")))
    )

def ParseDatetime(value: str | None, fmt: str = "%Y-%m-%dT%H:%M:%S") -> Result[datetime]:
    return (
        _require_string(value, "ParseDatetime")
        .Bind(lambda s: Result.Try(lambda: datetime.strptime(s, fmt), lambda e: ValueError(f"ParseDatetime: cannot parse {value!r} with format {fmt!r}: {e}")))
    )

def ParseTime(value: str | None, fmt: str = "%H:%M:%S") -> Result[time]:
    return (
        _require_string(value, "ParseTime")
        .Bind(lambda s: Result.Try(lambda: datetime.strptime(s, fmt).time(), lambda e: ValueError(f"ParseTime: cannot parse {value!r} with format {fmt!r}: {e}")))
    )

def ParseUuid(value: str | None) -> Result[UUID]:
    return (
        _require_string(value, "ParseUuid")
        .Bind(lambda s: Result.Try(lambda: UUID(s), lambda e: ValueError(f"ParseUuid: cannot parse {value!r}: {e}")))
    )

def ParseEnum(value: str | None, enum_type: Type[Enum], case_sensitive: bool = False) -> Result[Enum]:
    def _lookup(s: str) -> Result[Enum]:
        key = s if case_sensitive else s.upper()
        for member in enum_type:
            compare = member.name if case_sensitive else member.name.upper()
            if compare == key:
                return Result.Success(member)
        return Result.Fail(ValueError(f"ParseEnum: {value!r} is not a member of {enum_type.__name__}"))

    return _require_string(value, "ParseEnum").Bind(_lookup)

def ParseRegex(value: str | None, pattern: str, group: int | str = 0) -> Result[str]:
    def _match(s: str) -> Result[str]:
        m = re.search(pattern, s)
        if m is None:
            return Result.Fail(ValueError(f"ParseRegex: pattern {pattern!r} did not match {value!r}"))
        return Result.Try(lambda: m.group(group), lambda e: ValueError(f"ParseRegex: group {group!r} not found: {e}"))

    return _require_string(value, "ParseRegex").Bind(_match)
