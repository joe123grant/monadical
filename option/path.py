from __future__ import annotations

from pathlib import Path

from .option import Option


def IsFile(path: Path) -> bool:
    return path.is_file()

def IsDirectory(path: Path) -> bool:
    return path.is_dir()

def IsVisible(path: Path) -> bool:
    return not path.name.startswith(".")

def Exists(path: Path) -> bool:
    return path.exists()

def AsFile(path: str | Path | None) -> Option[Path]:
    return (
        Option.FromNullable(path)
        .Map(Path)
        .Filter(IsFile)
    )

def AsDirectory(path: str | Path | None) -> Option[Path]:
    return (
        Option.FromNullable(path)
        .Map(Path)
        .Filter(IsDirectory)
    )

def AsVisibleFile(path: str | Path | None) -> Option[Path]:
    return (
        Option.FromNullable(path)
        .Map(Path)
        .Filter(IsFile)
        .Filter(IsVisible)
    )
