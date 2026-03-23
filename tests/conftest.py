from __future__ import annotations

from enum import Enum

import pytest


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
 
@pytest.fixture
def sample_enum():
    return Color
 
@pytest.fixture
def text_file(tmp_path):
    filePath = tmp_path / "hello.txt"
    filePath.write_text("hello\nworld\n")
    return filePath
 
@pytest.fixture
def json_file(tmp_path):
    filePath = tmp_path / "data.json"
    filePath.write_text('{"key": "value"}')
    return filePath
 
@pytest.fixture
def empty_file(tmp_path):
    filePath = tmp_path / "empty.txt"
    filePath.write_bytes(b"")
    return filePath
 
@pytest.fixture
def hidden_file(tmp_path):
    filePath = tmp_path / ".hidden"
    filePath.write_text("secret")
    return filePath
 
@pytest.fixture
def sample_directory(tmp_path):
    directoryPath = tmp_path / "subdir"
    directoryPath.mkdir()
    return directoryPath
