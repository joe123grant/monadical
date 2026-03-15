from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .option import Option
from .path import AsFile

def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Option[str]:
    return AsFile(path).Bind(lambda p: Option.Try(lambda: p.read_text(encoding=encoding)))

def ReadBytes(path: str | Path | None) -> Option[bytes]:
    return AsFile(path).Bind(lambda p: Option.Try(lambda: p.read_bytes()))

def ReadLines(path: str | Path | None, encoding: str = "utf-8", strip: bool = False) -> Option[list[str]]:
    def _read(p: Path) -> list[str]:
        raw = p.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in raw if line.strip()]
        return raw

    return AsFile(path).Bind(lambda p: Option.Try(lambda: _read(p)))

def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Option[Any]:
    return ReadText(path, encoding=encoding).Bind(lambda text: Option.Try(lambda: json.loads(text)))

def ParseJson(text: str) -> Option[Any]:
    return Option.Try(lambda: json.loads(text))
