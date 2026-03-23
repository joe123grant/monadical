from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .option import Option
from .path import AsFile

def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Option[str]:
    return AsFile(path).Bind(lambda filePath: Option.Try(lambda: filePath.read_text(encoding=encoding)))

def ReadBytes(path: str | Path | None) -> Option[bytes]:
    return AsFile(path).Bind(lambda filePath: Option.Try(lambda: filePath.read_bytes()))

def ReadLines(path: str | Path | None, encoding: str = "utf-8", strip: bool = False) -> Option[list[str]]:
    def _ReadLines(filePath: Path) -> list[str]:
        lines = filePath.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in lines if line.strip()]
        return lines

    return AsFile(path).Bind(lambda filePath: Option.Try(lambda: _ReadLines(filePath)))

def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Option[Any]:
    return ReadText(path, encoding=encoding).Bind(lambda text: Option.Try(lambda: json.loads(text)))

def ParseJson(text: str) -> Option[Any]:
    return Option.Try(lambda: json.loads(text))
