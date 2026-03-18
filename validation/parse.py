from __future__ import annotations

import re
import math
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Type

from uuid import UUID

from .validation import Validation


_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})


def _validate_string(value: str | None, label: str) -> Validation[str, str]:
    if value is None:
        return Validation.Fail([f"{label}: value is None"])
    s = value.strip()
    if not s:
        return Validation.Fail([f"{label}: value is empty"])
    return Validation.Success(s)


def ParseInt(value: str | None, base: int = 10) -> Validation[int, str]:
    return (
        _validate_string(value, "ParseInt")
        .Bind(lambda s: Validation.Try(lambda: int(s, base), lambda e: [f"ParseInt: cannot parse {value!r}: {e}"]))
    )


def ParseFloat(value: str | None) -> Validation[float, str]:
    def _parse(s: str) -> Validation[float, str]:
        return (
            Validation.Try(lambda: float(s), lambda e: [f"ParseFloat: cannot parse {value!r}: {e}"])
            .Bind(lambda f: Validation.Success(f) if math.isfinite(f) else Validation.Fail([f"ParseFloat: {value!r} is not finite"]))
        )
    return _validate_string(value, "ParseFloat").Bind(_parse)


def ParseDecimal(value: str | None) -> Validation[Decimal, str]:
    def _parse(s: str) -> Validation[Decimal, str]:
        return (
            Validation.Try(lambda: Decimal(s), lambda e: [f"ParseDecimal: cannot parse {value!r}: {e}"])
            .Bind(lambda d: Validation.Success(d) if d.is_finite() else Validation.Fail([f"ParseDecimal: {value!r} is not finite"]))
        )
    return _validate_string(value, "ParseDecimal").Bind(_parse)


def ParseBool(value: Any, truthy: frozenset[str] = _TRUTHY, falsy: frozenset[str] = _FALSY) -> Validation[bool, str]:
    str_val = str(value) if value is not None else None

    def _lookup(s: str) -> Validation[bool, str]:
        lower = s.lower()
        if lower in truthy:
            return Validation.Success(True)
        if lower in falsy:
            return Validation.Success(False)
        return Validation.Fail([f"ParseBool: cannot interpret {value!r} as bool"])

    return _validate_string(str_val, "ParseBool").Bind(_lookup)


def ParseDate(value: str | None, fmt: str = "%Y-%m-%d") -> Validation[date, str]:
    return (
        _validate_string(value, "ParseDate")
        .Bind(lambda s: Validation.Try(lambda: datetime.strptime(s, fmt).date(), lambda e: [f"ParseDate: cannot parse {value!r} with format {fmt!r}: {e}"]))
    )


def ParseDatetime(value: str | None, fmt: str = "%Y-%m-%dT%H:%M:%S") -> Validation[datetime, str]:
    return (
        _validate_string(value, "ParseDatetime")
        .Bind(lambda s: Validation.Try(lambda: datetime.strptime(s, fmt), lambda e: [f"ParseDatetime: cannot parse {value!r} with format {fmt!r}: {e}"]))
    )


def ParseTime(value: str | None, fmt: str = "%H:%M:%S") -> Validation[time, str]:
    return (
        _validate_string(value, "ParseTime")
        .Bind(lambda s: Validation.Try(lambda: datetime.strptime(s, fmt).time(), lambda e: [f"ParseTime: cannot parse {value!r} with format {fmt!r}: {e}"]))
    )


def ParseUuid(value: str | None) -> Validation[UUID, str]:
    return (
        _validate_string(value, "ParseUuid")
        .Bind(lambda s: Validation.Try(lambda: UUID(s), lambda e: [f"ParseUuid: cannot parse {value!r}: {e}"]))
    )


def ParseEnum(value: str | None, enum_type: Type[Enum], case_sensitive: bool = False) -> Validation[Enum, str]:
    def _lookup(s: str) -> Validation[Enum, str]:
        key = s if case_sensitive else s.upper()
        for member in enum_type:
            compare = member.name if case_sensitive else member.name.upper()
            if compare == key:
                return Validation.Success(member)
        return Validation.Fail([f"ParseEnum: {value!r} is not a member of {enum_type.__name__}"])

    return _validate_string(value, "ParseEnum").Bind(_lookup)


def ParseRegex(value: str | None, pattern: str, group: int | str = 0) -> Validation[str, str]:
    def _match(s: str) -> Validation[str, str]:
        m = re.search(pattern, s)
        if m is None:
            return Validation.Fail([f"ParseRegex: pattern {pattern!r} did not match {value!r}"])
        return Validation.Try(lambda: m.group(group), lambda e: [f"ParseRegex: group {group!r} not found: {e}"])

    return _validate_string(value, "ParseRegex").Bind(_match)
