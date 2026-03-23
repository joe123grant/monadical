from __future__ import annotations

from option.env import GetEnv, GetEnvBool, GetEnvFloat, GetEnvInt



def test_get_env_returns_some_for_present_value(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_VALUE", "hello")
    result = GetEnv("OPTION_TEST_VALUE")
    assert result.IsSome()
    assert result.Unwrap() == "hello"



def test_get_env_returns_empty_for_missing_value(monkeypatch):
    monkeypatch.delenv("OPTION_TEST_MISSING", raising=False)
    result = GetEnv("OPTION_TEST_MISSING")
    assert result.IsEmpty()



def test_get_env_returns_empty_for_blank_value(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_BLANK", "   ")
    result = GetEnv("OPTION_TEST_BLANK")
    assert result.IsEmpty()



def test_get_env_int_parses_integer(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_INT", "42")
    result = GetEnvInt("OPTION_TEST_INT")
    assert result.IsSome()
    assert result.Unwrap() == 42



def test_get_env_int_returns_empty_for_invalid_integer(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_INT_BAD", "abc")
    result = GetEnvInt("OPTION_TEST_INT_BAD")
    assert result.IsEmpty()



def test_get_env_float_parses_float(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_FLOAT", "3.14")
    result = GetEnvFloat("OPTION_TEST_FLOAT")
    assert result.IsSome()
    assert result.Unwrap() == 3.14



def test_get_env_float_returns_empty_for_invalid_float(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_FLOAT_BAD", "nan")
    result = GetEnvFloat("OPTION_TEST_FLOAT_BAD")
    assert result.IsEmpty()



def test_get_env_bool_parses_boolean(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_BOOL", "yes")
    result = GetEnvBool("OPTION_TEST_BOOL")
    assert result.IsSome()
    assert result.Unwrap() is True



def test_get_env_bool_returns_empty_for_invalid_boolean(monkeypatch):
    monkeypatch.setenv("OPTION_TEST_BOOL_BAD", "maybe")
    result = GetEnvBool("OPTION_TEST_BOOL_BAD")
    assert result.IsEmpty()
