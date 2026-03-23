from __future__ import annotations

import os

from .option import Option
from .parse import ParseBool, ParseFloat, ParseInt


def GetEnv(key: str) -> Option[str]:
    return Option.FromNullableString(os.environ.get(key), strip=True)

def GetEnvInt(key: str, base: int = 10) -> Option[int]:
    return GetEnv(key).Bind(lambda value: ParseInt(value, base))

def GetEnvFloat(key: str) -> Option[float]:
    return GetEnv(key).Bind(ParseFloat)

def GetEnvBool(key: str) -> Option[bool]:
    return GetEnv(key).Bind(ParseBool)
