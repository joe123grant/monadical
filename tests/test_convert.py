from __future__ import annotations
 
import pytest
 
from convert import OptionToResult, ResultToOption
from option.option import Option, Some
from result.result import Result, Ok, Failure
 
def test_option_to_result_some_returns_ok():
    result = OptionToResult(Option.Some(42), ValueError("unused"))
    assert result.IsSuccess()
    assert result == Ok(42)
 
def test_option_to_result_empty_returns_failure():
    error = ValueError("missing")
    result = OptionToResult(Option.Empty(), error)
    assert result.IsFailure()
    assert isinstance(result, Failure)
    assert result.error is error
 
def test_result_to_option_ok_returns_some():
    option = ResultToOption(Result.Success(42))
    assert option.IsSome()
    assert option == Option.Some(42)
 
def test_result_to_option_failure_returns_empty():
    option = ResultToOption(Result.Fail(ValueError("oops")))
    assert option.IsEmpty()
 
def test_round_trip_some_to_result_to_option():
    original = Option.Some(99)
    error = ValueError("should not be used")
    assert ResultToOption(OptionToResult(original, error)) == original
 
def test_round_trip_ok_to_option_to_result():
    original = Result.Success(99)
    error = ValueError("should not be used")
    assert OptionToResult(ResultToOption(original), error) == original
 
def test_option_to_result_preserves_value_type():
    result = OptionToResult(Option.Some("hello"), ValueError("unused"))
    assert result == Ok("hello")
 
def test_result_to_option_preserves_value_type():
    option = ResultToOption(Result.Success("hello"))
    assert option == Option.Some("hello")
