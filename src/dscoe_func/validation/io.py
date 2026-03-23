from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .path import ValidateFile
from .validation import Validation


def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Validation[str, str]:
    return ValidateFile(path).Bind(
        lambda filePath: Validation.Try(
            lambda: filePath.read_text(encoding=encoding),
            lambda exception: [f"ReadText: failed to read {path!r}: {exception}"],
        )
    )

def ReadBytes(path: str | Path | None) -> Validation[bytes, str]:
    return ValidateFile(path).Bind(
        lambda filePath: Validation.Try(
            lambda: filePath.read_bytes(),
            lambda exception: [f"ReadBytes: failed to read {path!r}: {exception}"],
        )
    )

def ReadLines(
    path: str | Path | None, encoding: str = "utf-8", strip: bool = False
) -> Validation[list[str], str]:
    def _ReadLines(filePath: Path) -> list[str]:
        lines = filePath.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in lines if line.strip()]
        return lines
    return ValidateFile(path).Bind(
        lambda filePath: Validation.Try(
            lambda: _ReadLines(filePath),
            lambda exception: [f"ReadLines: failed to read {path!r}: {exception}"],
        )
    )

def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Validation[Any, str]:
    return ReadText(path, encoding=encoding).Bind(
        lambda text: Validation.Try(
            lambda: json.loads(text),
            lambda exception: [f"ReadJson: failed to parse JSON from {path!r}: {exception}"],
        )
    )

def ParseJson(text: str) -> Validation[Any, str]:
    return Validation.Try(
        lambda: json.loads(text),
        lambda exception: [f"ParseJson: invalid JSON: {exception}"],
    )
