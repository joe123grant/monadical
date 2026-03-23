from __future__ import annotations

from dscoe_func.option.path import AsDirectory, AsFile, AsVisibleFile, IsDirectory, IsFile


def test_is_file_returns_some_for_existing_file(text_file):
    result = IsFile(text_file)
    assert result.IsSome()
    assert result.Unwrap() == text_file
 
def test_is_file_returns_empty_for_missing_path(tmp_path):
    result = IsFile(tmp_path / "missing.txt")
    assert result.IsEmpty()
 
def test_is_directory_returns_some_for_existing_directory(sample_directory):
    result = IsDirectory(sample_directory)
    assert result.IsSome()
    assert result.Unwrap() == sample_directory
 
def test_is_directory_returns_empty_for_missing_path(tmp_path):
    result = IsDirectory(tmp_path / "missing")
    assert result.IsEmpty()
 
def test_as_file_returns_some_for_existing_file(text_file):
    result = AsFile(text_file)
    assert result.IsSome()
    assert result.Unwrap() == text_file
 
def test_as_file_returns_empty_for_directory(sample_directory):
    result = AsFile(sample_directory)
    assert result.IsEmpty()
 
def test_as_directory_returns_some_for_existing_directory(sample_directory):
    result = AsDirectory(sample_directory)
    assert result.IsSome()
    assert result.Unwrap() == sample_directory
 
def test_as_directory_returns_empty_for_file(text_file):
    result = AsDirectory(text_file)
    assert result.IsEmpty()
 
def test_as_visible_file_returns_some_for_non_hidden_file(text_file):
    result = AsVisibleFile(text_file)
    assert result.IsSome()
    assert result.Unwrap() == text_file
 
def test_as_visible_file_returns_empty_for_hidden_file(hidden_file):
    result = AsVisibleFile(hidden_file)
    assert result.IsEmpty()
