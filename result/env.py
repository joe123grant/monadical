from __future__ import annotations

import os

from .result import Result
from .parse import ParseBool, ParseFloat, ParseInt

def RequireEnv(key: str) -> Result[str]:
    val = os.environ.get(key)
    if val is None:
        return Result.Fail(KeyError(f"Environment variable {key!r} is not set"))
    if not val.strip():
        return Result.Fail(ValueError(f"Environment variable {key!r} is empty"))
    return Result.Success(val)

def RequireEnvInt(key: str, base: int = 10) -> Result[int]:
    return RequireEnv(key).Bind(lambda v: ParseInt(v, base))

def RequireEnvFloat(key: str) -> Result[float]:
    return RequireEnv(key).Bind(ParseFloat)

def RequireEnvBool(key: str) -> Result[bool]:
    return RequireEnv(key).Bind(ParseBool)
