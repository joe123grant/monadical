from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .result import Result
from .path import RequireFile


def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Result[str]:
    return RequireFile(path).Bind(lambda p: Result.Try(lambda: p.read_text(encoding=encoding)))

def ReadBytes(path: str | Path | None) -> Result[bytes]:
    return RequireFile(path).Bind(lambda p: Result.Try(lambda: p.read_bytes()))

def ReadLines(path: str | Path | None, encoding: str = "utf-8", strip: bool = False) -> Result[list[str]]:
    def _read(p: Path) -> list[str]:
        raw = p.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in raw if line.strip()]
        return raw

    return RequireFile(path).Bind(lambda p: Result.Try(lambda: _read(p)))

def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Result[Any]:
    return ReadText(path, encoding=encoding).Bind(lambda text: Result.Try(lambda: json.loads(text)))

def ParseJson(text: str) -> Result[Any]:
    return Result.Try(lambda: json.loads(text))
