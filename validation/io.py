from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .validation import Validation
from .path import ValidateFile


def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Validation[str, str]:
    return ValidateFile(path).Then(
        lambda p: Validation.Try(lambda: p.read_text(encoding=encoding), lambda e: [f"ReadText: failed to read {path!r}: {e}"])
    )


def ReadBytes(path: str | Path | None) -> Validation[bytes, str]:
    return ValidateFile(path).Then(
        lambda p: Validation.Try(lambda: p.read_bytes(), lambda e: [f"ReadBytes: failed to read {path!r}: {e}"])
    )


def ReadLines(path: str | Path | None, encoding: str = "utf-8", strip: bool = False) -> Validation[list[str], str]:
    def _read(p: Path) -> list[str]:
        raw = p.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in raw if line.strip()]
        return raw

    return ValidateFile(path).Then(
        lambda p: Validation.Try(lambda: _read(p), lambda e: [f"ReadLines: failed to read {path!r}: {e}"])
    )


def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Validation[Any, str]:
    return ReadText(path, encoding=encoding).Then(
        lambda text: Validation.Try(lambda: json.loads(text), lambda e: [f"ReadJson: failed to parse JSON from {path!r}: {e}"])
    )


def ParseJson(text: str) -> Validation[Any, str]:
    return Validation.Try(lambda: json.loads(text), lambda e: [f"ParseJson: invalid JSON: {e}"])
