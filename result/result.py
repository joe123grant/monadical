from __future__ import annotations

import hashlib
from pathlib import Path

from .result import Result
from ..option.path import AsFile, AsDirectory, AsVisibleFile


class EmptyFileError(Exception):
    """Raised when a file exists but contains 0 bytes of data."""
    pass

def RequireFile(path: str | Path | None) -> Result[Path]:
    return AsFile(path).ToResult(ValueError(f"Not a valid file: {path!r}"))

def RequireDirectory(path: str | Path | None) -> Result[Path]:
    return AsDirectory(path).ToResult(ValueError(f"Not a valid directory: {path!r}"))

def RequireVisibleFile(path: str | Path | None) -> Result[Path]:
    return AsVisibleFile(path).ToResult(ValueError(f"Not a valid or visible file: {path!r}"))

def ComputeFileHash(path: Path) -> Result[str]:
    def _Compute() -> str:
        if path.stat().st_size == 0:
            raise EmptyFileError(f"File {path.name!r} is empty (0 bytes).")

        digest = hashlib.sha256()
        with path.open("rb") as file:
            while chunk := file.read(4096):
                digest.update(chunk)
        return digest.hexdigest()

    return Result.Try(_Compute)

