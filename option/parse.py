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
    """
    Safely parse a string as an integer.

    Accepts nullable input for pipeline compatibility. Strips whitespace before parsing.

    Args:
        value: The string to parse (nullable).
        base: Numeric base (default: 10). Supports 2-36.

    Returns:
        `Some(int)` if parsing succeeded, otherwise `Empty()`.

    Example:
        ParseInt("42")         # Some(42)
        ParseInt("  -7  ")    # Some(-7)
        ParseInt("0xff", 16)  # Some(255)
        ParseInt("abc")       # Empty()
        ParseInt(None)        # Empty()
    """
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: int(s, base), ValueError))
    )


def ParseFloat(value: str | None) -> Option[float]:
    """
    Safely parse a string as a float.

    Accepts nullable input for pipeline compatibility. Strips whitespace before parsing.
    Rejects `inf` and `nan` — use `ParseFloatPermissive` if you need those.

    Args:
        value: The string to parse (nullable).

    Returns:
        `Some(float)` if parsing succeeded and result is finite, otherwise `Empty()`.

    Example:
        ParseFloat("3.14")     # Some(3.14)
        ParseFloat("  -0.5 ") # Some(-0.5)
        ParseFloat("inf")     # Empty()
        ParseFloat("nope")    # Empty()
        ParseFloat(None)      # Empty()
    """
    import math
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: float(s), ValueError))
            .Filter(math.isfinite)
    )


def ParseDecimal(value: str | None) -> Option[Decimal]:
    """
    Safely parse a string as a `Decimal`.

    Use this for money, measurements, or anywhere floating-point imprecision is unacceptable.
    Strips whitespace before parsing. Rejects special values like `Infinity` and `NaN`.

    Args:
        value: The string to parse (nullable).

    Returns:
        `Some(Decimal)` if parsing succeeded and result is finite, otherwise `Empty()`.

    Example:
        ParseDecimal("19.99")    # Some(Decimal('19.99'))
        ParseDecimal("  1000 ")  # Some(Decimal('1000'))
        ParseDecimal("nope")     # Empty()
        ParseDecimal(None)       # Empty()
    """
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
    """
    Safely parse a string as a boolean.

    Normalises to lowercase before checking. By default recognises:
    - Truthy: "true", "1", "yes", "on", "y"
    - Falsy: "false", "0", "no", "off", "n"

    Returns `Empty()` if the string doesn't match any recognised value.
    You can supply your own `truthy`/`falsy` sets for domain-specific parsing.

    Args:
        value: The string to parse (nullable).
        truthy: Set of lowercase strings that map to True.
        falsy: Set of lowercase strings that map to False.

    Returns:
        `Some(True)` or `Some(False)` if recognised, otherwise `Empty()`.

    Example:
        ParseBool("yes")     # Some(True)
        ParseBool("0")       # Some(False)
        ParseBool("maybe")   # Empty()
        ParseBool(None)      # Empty()
    """
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
    """
    Safely parse a string as a `date`.

    Strips whitespace before parsing. Uses `strptime` with the given format.

    Args:
        value: The string to parse (nullable).
        fmt: Date format string (default: ISO 8601 date `%Y-%m-%d`).

    Returns:
        `Some(date)` if parsing succeeded, otherwise `Empty()`.

    Example:
        ParseDate("2024-03-14")               # Some(date(2024, 3, 14))
        ParseDate("14/03/2024", "%d/%m/%Y")   # Some(date(2024, 3, 14))
        ParseDate("not a date")               # Empty()
        ParseDate(None)                        # Empty()
    """
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: datetime.strptime(s, fmt).date(), ValueError))
    )


def ParseDatetime(value: str | None, fmt: str = "%Y-%m-%dT%H:%M:%S") -> Option[datetime]:
    """
    Safely parse a string as a `datetime`.

    Strips whitespace before parsing. Uses `strptime` with the given format.

    Args:
        value: The string to parse (nullable).
        fmt: Datetime format string (default: ISO 8601 without timezone `%Y-%m-%dT%H:%M:%S`).

    Returns:
        `Some(datetime)` if parsing succeeded, otherwise `Empty()`.

    Example:
        ParseDatetime("2024-03-14T10:30:00")                           # Some(datetime(...))
        ParseDatetime("14/03/2024 10:30", "%d/%m/%Y %H:%M")           # Some(datetime(...))
        ParseDatetime("not a datetime")                                 # Empty()
        ParseDatetime(None)                                             # Empty()
    """
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: datetime.strptime(s, fmt), ValueError))
    )


def ParseTime(value: str | None, fmt: str = "%H:%M:%S") -> Option[time]:
    """
    Safely parse a string as a `time`.

    Strips whitespace before parsing. Uses `strptime` with the given format.

    Args:
        value: The string to parse (nullable).
        fmt: Time format string (default: `%H:%M:%S`).

    Returns:
        `Some(time)` if parsing succeeded, otherwise `Empty()`.

    Example:
        ParseTime("14:30:00")          # Some(time(14, 30, 0))
        ParseTime("2:30 PM", "%I:%M %p")  # Some(time(14, 30))
        ParseTime("not a time")        # Empty()
        ParseTime(None)                # Empty()
    """
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: datetime.strptime(s, fmt).time(), ValueError))
    )


def ParseUuid(value: str | None) -> Option[UUID]:
    """
    Safely parse a string as a UUID.

    Accepts all standard UUID formats (with or without hyphens, braces, urn prefix).
    Strips whitespace before parsing.

    Args:
        value: The string to parse (nullable).

    Returns:
        `Some(UUID)` if parsing succeeded, otherwise `Empty()`.

    Example:
        ParseUuid("550e8400-e29b-41d4-a716-446655440000")  # Some(UUID(...))
        ParseUuid("550e8400e29b41d4a716446655440000")       # Some(UUID(...))
        ParseUuid("not-a-uuid")                              # Empty()
        ParseUuid(None)                                      # Empty()
    """
    return (
        Option.FromNullableString(value, strip=True)
            .Bind(lambda s: Option.Try(lambda: UUID(s), ValueError))
    )


def ParseEnum(value: str | None, enum_type: Type[Enum], case_sensitive: bool = False) -> Option[Enum]:
    """
    Safely parse a string as a member of a Python Enum.

    By default performs a case-insensitive lookup against member *names*.
    Use `case_sensitive=True` for exact matching.

    Args:
        value: The string to parse (nullable).
        enum_type: The Enum class to look up against.
        case_sensitive: If False (default), normalise to uppercase for matching.

    Returns:
        `Some(member)` if a matching member was found, otherwise `Empty()`.

    Example:
        class Colour(Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        ParseEnum("red", Colour)     # Some(Colour.RED)
        ParseEnum("RED", Colour)     # Some(Colour.RED)
        ParseEnum("purple", Colour)  # Empty()
        ParseEnum(None, Colour)      # Empty()
    """
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
    """
    Safely extract a regex match group from a string.

    Use this when you need to pull a structured value out of unstructured text.
    Returns `Empty()` if the string is empty/None, the pattern doesn't match,
    or the specified group doesn't exist.

    Args:
        value: The string to search (nullable).
        pattern: Regular expression pattern.
        group: Capture group index (int) or name (str). Defaults to 0 (entire match).

    Returns:
        `Some(matched_text)` if the pattern matched and the group exists, otherwise `Empty()`.

    Example:
        ParseRegex("Order #12345", r"#(\\d+)", group=1)    # Some("12345")
        ParseRegex("no match here", r"#(\\d+)", group=1)   # Empty()
        ParseRegex(None, r"\\d+")                           # Empty()

        # Named groups
        ParseRegex("2024-03-14", r"(?P<year>\\d{4})-(?P<month>\\d{2})", group="year")  # Some("2024")
    """
    return (
        Option.FromNullableString(value)
            .Bind(lambda s: Option.FromNullable(re.search(pattern, s)))
            .Bind(lambda m: Option.Try(lambda: m.group(group), (IndexError, re.error)))
    )
