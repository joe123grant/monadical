from __future__ import annotations

from option.io import ParseJson, ReadBytes, ReadJson, ReadLines, ReadText

def test_read_text_returns_file_content(text_file):
    result = ReadText(text_file)
    assert result.IsSome()
    assert result.Unwrap() == "hello\nworld\n"

def test_read_text_returns_empty_for_missing_file(tmp_path):
    result = ReadText(tmp_path / "missing.txt")
    assert result.IsEmpty()

def test_read_bytes_returns_file_content(text_file):
    result = ReadBytes(text_file)
    assert result.IsSome()
    assert result.Unwrap() == b"hello\nworld\n"

def test_read_bytes_returns_empty_for_missing_file(tmp_path):
    result = ReadBytes(tmp_path / "missing.bin")
    assert result.IsEmpty()

def test_read_lines_returns_lines(text_file):
    result = ReadLines(text_file)
    assert result.IsSome()
    assert result.Unwrap() == ["hello\n", "world\n"]

def test_read_lines_supports_strip(text_file):
    result = ReadLines(text_file, strip=True)
    assert result.IsSome()
    assert result.Unwrap() == ["hello", "world"]

def test_read_json_returns_parsed_object(json_file):
    result = ReadJson(json_file)
    assert result.IsSome()
    assert result.Unwrap() == {"key": "value"}

def test_read_json_returns_empty_for_missing_file(tmp_path):
    result = ReadJson(tmp_path / "missing.json")
    assert result.IsEmpty()

def test_read_json_returns_empty_for_invalid_json(invalid_json_file):
    result = ReadJson(invalid_json_file)
    assert result.IsEmpty()

def test_parse_json_returns_parsed_object():
    result = ParseJson('{"key": "value"}')
    assert result.IsSome()
    assert result.Unwrap() == {"key": "value"}

def test_parse_json_returns_empty_for_invalid_json():
    result = ParseJson('{"key": }')
    assert result.IsEmpty()
