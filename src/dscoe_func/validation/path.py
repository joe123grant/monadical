from __future__ import annotations

from pathlib import Path

from ..option.path import AsDirectory, AsFile, AsVisibleFile
from .validation import Validation


def ValidateFile(path: str | Path | None) -> Validation[Path, str]:
    return AsFile(path).Match(
        Validation.Success, lambda: Validation.Fail([f"Not a valid file: {path!r}"])
    )

def ValidateDirectory(path: str | Path | None) -> Validation[Path, str]:
    return AsDirectory(path).Match(
        Validation.Success,
        lambda: Validation.Fail([f"Not a valid directory: {path!r}"]),
    )

def ValidateVisibleFile(path: str | Path | None) -> Validation[Path, str]:
    return AsVisibleFile(path).Match(
        Validation.Success,
        lambda: Validation.Fail([f"Not a valid or visible file: {path!r}"]),
    )
