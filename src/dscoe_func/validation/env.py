from __future__ import annotations

import os

from .parse import ParseBool, ParseFloat, ParseInt
from .validation import Validation


def ValidateEnv(key: str) -> Validation[str, str]:
    value = os.environ.get(key)
    if value is None:
        return Validation.Fail([f"Environment variable {key!r} is not set"])
    if not value.strip():
        return Validation.Fail([f"Environment variable {key!r} is empty"])
    return Validation.Success(value)

def ValidateEnvInt(key: str, base: int = 10) -> Validation[int, str]:
    return ValidateEnv(key).Bind(lambda value: ParseInt(value, base))

def ValidateEnvFloat(key: str) -> Validation[float, str]:
    return ValidateEnv(key).Bind(ParseFloat)

def ValidateEnvBool(key: str) -> Validation[bool, str]:
    return ValidateEnv(key).Bind(ParseBool)
