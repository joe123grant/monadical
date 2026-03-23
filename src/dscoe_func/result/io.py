from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .path import RequireFile
from .result import Result


def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Result[str]:
    return RequireFile(path).Bind(
        lambda filePath: Result.Try(lambda: filePath.read_text(encoding=encoding))
    )

def ReadBytes(path: str | Path | None) -> Result[bytes]:
    return RequireFile(path).Bind(lambda filePath: Result.Try(lambda: filePath.read_bytes()))

def ReadLines(
    path: str | Path | None, encoding: str = "utf-8", strip: bool = False
) -> Result[list[str]]:
    def _ReadLines(filePath: Path) -> list[str]:
        lines = filePath.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in lines if line.strip()]
        return lines
    return RequireFile(path).Bind(lambda filePath: Result.Try(lambda: _ReadLines(filePath)))

def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Result[Any]:
    return ReadText(path, encoding=encoding).Bind(lambda text: Result.Try(lambda: json.loads(text)))

def ParseJson(text: str) -> Result[Any]:
    return Result.Try(lambda: json.loads(text))
