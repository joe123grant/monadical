from __future__ import annotations
 
import uuid
from datetime import date, datetime, time
from decimal import Decimal
 
import pytest
 
from option.parse import ParseBool, ParseDate, ParseDatetime, ParseDecimal, ParseEnum, ParseFloat, ParseInt, ParseRegex, ParseTime, ParseUuid
 
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("42", 42),
        (" 7 ", 7),
        ("ff", 255),
    ],
)
def test_parse_int_returns_some_for_valid_inputs(text, expected):
    if text == "ff":
        result = ParseInt(text, base=16)
    else:
        result = ParseInt(text)
 
    assert result.IsSome()
    assert result.Unwrap() == expected
 
@pytest.mark.parametrize("text", [None, "", "abc", "3.14"])
def test_parse_int_returns_empty_for_invalid_inputs(text):
    result = ParseInt(text)
    assert result.IsEmpty()
 
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.14", 3.14),
        ("-0.5", -0.5),
    ],
)
def test_parse_float_returns_some_for_valid_inputs(text, expected):
    result = ParseFloat(text)
    assert result.IsSome()
    assert result.Unwrap() == expected
 
@pytest.mark.parametrize("text", [None, "", "inf", "-inf", "nan", "abc"])
def test_parse_float_returns_empty_for_invalid_inputs(text):
    result = ParseFloat(text)
    assert result.IsEmpty()
 
def test_parse_decimal_returns_some_for_valid_input():
    result = ParseDecimal("1.23")
    assert result.IsSome()
    assert result.Unwrap() == Decimal("1.23")
 
@pytest.mark.parametrize("text", [None, "Infinity", "NaN"])
def test_parse_decimal_returns_empty_for_invalid_inputs(text):
    result = ParseDecimal(text)
    assert result.IsEmpty()
 
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("true", True),
        ("YES", True),
        ("1", True),
        ("off", False),
        ("n", False),
    ],
)
def test_parse_bool_returns_some_for_valid_inputs(text, expected):
    result = ParseBool(text)
    assert result.IsSome()
    assert result.Unwrap() is expected
 
@pytest.mark.parametrize("text", [None, "maybe", ""])
def test_parse_bool_returns_empty_for_invalid_inputs(text):
    result = ParseBool(text)
    assert result.IsEmpty()
 
def test_parse_date_returns_some_for_valid_input():
    result = ParseDate("2024-01-15")
    assert result.IsSome()
    assert result.Unwrap() == date(2024, 1, 15)
 
@pytest.mark.parametrize("text", [None, "not-a-date", "15/01/2024"])
def test_parse_date_returns_empty_for_invalid_inputs(text):
    result = ParseDate(text)
    assert result.IsEmpty()
 
def test_parse_datetime_returns_some_for_valid_input():
    result = ParseDatetime("2024-01-15T12:00:00")
    assert result.IsSome()
    assert result.Unwrap() == datetime(2024, 1, 15, 12, 0, 0)
 
@pytest.mark.parametrize("text", [None, "2024-01-15", "not-a-datetime"])
def test_parse_datetime_returns_empty_for_invalid_inputs(text):
    result = ParseDatetime(text)
    assert result.IsEmpty()
 
def test_parse_time_returns_some_for_valid_input():
    result = ParseTime("14:30:00")
    assert result.IsSome()
    assert result.Unwrap() == time(14, 30, 0)
 
@pytest.mark.parametrize("text", [None, "14:30", "not-a-time"])
def test_parse_time_returns_empty_for_invalid_inputs(text):
    result = ParseTime(text)
    assert result.IsEmpty()
 
def test_parse_uuid_returns_some_for_valid_input():
    value = str(uuid.uuid4())
    result = ParseUuid(value)
    assert result.IsSome()
    assert result.Unwrap() == uuid.UUID(value)
 
@pytest.mark.parametrize("text", [None, "not-a-uuid"])
def test_parse_uuid_returns_empty_for_invalid_inputs(text):
    result = ParseUuid(text)
    assert result.IsEmpty()
 
def test_parse_enum_returns_some_for_case_insensitive_match(sample_enum):
    result = ParseEnum("red", sample_enum)
    assert result.IsSome()
    assert result.Unwrap() == sample_enum.RED
 
@pytest.mark.parametrize("text", [None, "PURPLE"])
def test_parse_enum_returns_empty_for_invalid_inputs(text, sample_enum):
    result = ParseEnum(text, sample_enum)
    assert result.IsEmpty()
 
def test_parse_regex_returns_some_for_matching_text():
    result = ParseRegex(r"(?P<number>\\d+)", "123", group="number")
    assert result.IsSome()
    assert result.Unwrap() == "123"
 
@pytest.mark.parametrize(
    ("pattern", "text", "group"),
    [
        (r"(?P<number>\\d+)", None, "number"),
        (r"(?P<number>\\d+)", "abc", "number"),
        (r"(?P<number>\\d+)", "123", "missing"),
    ],
)
def test_parse_regex_returns_empty_for_invalid_inputs(pattern, text, group):
    result = ParseRegex(pattern, text, group=group)
    assert result.IsEmpty()
