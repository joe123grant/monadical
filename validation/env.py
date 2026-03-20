from __future__ import annotations

import os

from .validation import Validation
from .parse import ParseBool, ParseFloat, ParseInt


def ValidateEnv(key: str) -> Validation[str, str]:
    val = os.environ.get(key)
    if val is None:
        return Validation.Fail([f"Environment variable {key!r} is not set"])
    if not val.strip():
        return Validation.Fail([f"Environment variable {key!r} is empty"])
    return Validation.Success(val)

def ValidateEnvInt(key: str, base: int = 10) -> Validation[int, str]:
    return ValidateEnv(key).Then(lambda v: ParseInt(v, base))

def ValidateEnvFloat(key: str) -> Validation[float, str]:
    return ValidateEnv(key).Then(ParseFloat)

def ValidateEnvBool(key: str) -> Validation[bool, str]:
    return ValidateEnv(key).Then(ParseBool)
