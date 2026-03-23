from __future__ import annotations

from pathlib import Path

from .option import Option


def IsFile(path: Path) -> Option[Path]:
    return Option.Some(path) if path.is_file() else Option.Empty()

def IsDirectory(path: Path) -> Option[Path]:
    return Option.Some(path) if path.is_dir() else Option.Empty()

def IsVisible(path: Path) -> bool:
    return not path.name.startswith(".")

def Exists(path: Path) -> bool:
    return path.exists()

def AsFile(path: str | Path | None) -> Option[Path]:
    return (
        Option.FromNullable(path)
        .Map(Path)
        .Filter(lambda p: p.is_file())
    )

def AsDirectory(path: str | Path | None) -> Option[Path]:
    return (
        Option.FromNullable(path)
        .Map(Path)
        .Filter(lambda p: p.is_dir())
    )

def AsVisibleFile(path: str | Path | None) -> Option[Path]:
    return (
        Option.FromNullable(path)
        .Map(Path)
        .Filter(lambda p: p.is_file())
        .Filter(IsVisible)
    )
