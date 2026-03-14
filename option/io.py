from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .option import Option
from .path import AsFile


def ReadText(path: str | Path | None, encoding: str = "utf-8") -> Option[str]:
    """
    Safely read an entire file as a string.

    Returns `Empty()` if the path is not a valid file or the read fails for any reason
    (missing file, permission error, encoding error etc).

    Args:
        path: Path to the file (nullable for pipeline compatibility).
        encoding: Text encoding to use (default: utf-8).

    Returns:
        `Some(content)` if reading succeeded, otherwise `Empty()`.

    Example:
        content: Option[str] = ReadText("/etc/hostname")
        content: Option[str] = ReadText(None)
    """
    return AsFile(path).Bind(
        lambda p: Option.Try(lambda: p.read_text(encoding=encoding))
    )


def ReadBytes(path: str | Path | None) -> Option[bytes]:
    """
    Safely read an entire file as raw bytes.

    Returns `Empty()` if the path is not a valid file or the read fails for any reason.

    Args:
        path: Path to the file (nullable for pipeline compatibility).

    Returns:
        `Some(bytes)` if reading succeeded, otherwise `Empty()`.

    Example:
        data: Option[bytes] = ReadBytes("image.png")
    """
    return AsFile(path).Bind(
        lambda p: Option.Try(lambda: p.read_bytes())
    )


def ReadLines(path: str | Path | None, encoding: str = "utf-8", strip: bool = False) -> Option[list[str]]:
    """
    Safely read a file and split it into lines.

    Returns `Empty()` if the path is not a valid file or the read fails for any reason.

    Args:
        path: Path to the file (nullable for pipeline compatibility).
        encoding: Text encoding to use (default: utf-8).
        strip: If True, strip whitespace from each line and discard empty lines.

    Returns:
        `Some(lines)` if reading succeeded, otherwise `Empty()`.

    Example:
        lines: Option[list[str]] = ReadLines("data.csv")
        lines: Option[list[str]] = ReadLines("data.csv", strip=True)
    """
    def _read(p: Path) -> list[str]:
        raw = p.read_text(encoding=encoding).splitlines()
        if strip:
            return [line.strip() for line in raw if line.strip()]
        return raw

    return AsFile(path).Bind(
        lambda p: Option.Try(lambda: _read(p))
    )


def ReadJson(path: str | Path | None, encoding: str = "utf-8") -> Option[Any]:
    """
    Safely read and parse a JSON file.

    Returns `Empty()` if the path is not a valid file, the read fails, or the content
    is not valid JSON.

    Args:
        path: Path to the file (nullable for pipeline compatibility).
        encoding: Text encoding to use (default: utf-8).

    Returns:
        `Some(parsed)` if reading and parsing succeeded, otherwise `Empty()`.

    Example:
        config: Option[dict] = ReadJson("config.json")
        settings = ReadJson("settings.json").Map(lambda d: d.get("timeout"))
    """
    return ReadText(path, encoding=encoding).Bind(
        lambda text: Option.Try(lambda: json.loads(text))
    )


def ParseJson(text: str) -> Option[Any]:
    """
    Safely parse a JSON string.

    Use this when you already have the text content and just want safe parsing
    without try/catch.

    Args:
        text: The raw JSON string.

    Returns:
        `Some(parsed)` if parsing succeeded, otherwise `Empty()`.

    Example:
        data: Option[dict] = ParseJson('{"key": "value"}')
        broken: Option[dict] = ParseJson('not json')
    """
    return Option.Try(lambda: json.loads(text))
