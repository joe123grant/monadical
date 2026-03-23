from __future__ import annotations

import os

from .parse import ParseBool, ParseFloat, ParseInt
from .result import Result


def RequireEnv(key: str) -> Result[str]:
    value = os.environ.get(key)
    if value is None:
        return Result.Fail(KeyError(f"Environment variable {key!r} is not set"))
    if not value.strip():
        return Result.Fail(ValueError(f"Environment variable {key!r} is empty"))
    return Result.Success(value)

def RequireEnvInt(key: str, base: int = 10) -> Result[int]:
    return RequireEnv(key).Bind(lambda value: ParseInt(value, base))

def RequireEnvFloat(key: str) -> Result[float]:
    return RequireEnv(key).Bind(ParseFloat)

def RequireEnvBool(key: str) -> Result[bool]:
    return RequireEnv(key).Bind(ParseBool)
