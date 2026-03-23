from __future__ import annotations
 
from ..option.Option.combinators import Choose, Partition, Sequence, Somes, Traverse
from option.option import Option
from option.parse import ParseInt
 
def test_somes_returns_only_present_values():
    values = Somes([Option.Some(1), Option.Empty(), Option.Some(3)])
    assert values == [1, 3]
 
def test_sequence_returns_some_when_all_options_are_present():
    result = Sequence([Option.Some(1), Option.Some(2)])
    assert result == Option.Some([1, 2])
 
def test_sequence_returns_empty_when_any_option_is_empty():
    result = Sequence([Option.Some(1), Option.Empty()])
    assert result.IsEmpty()
 
def test_traverse_maps_and_sequences_successfully():
    result = Traverse(["1", "2"], ParseInt)
    assert result == Option.Some([1, 2])
 
def test_traverse_returns_empty_on_first_failed_parse():
    result = Traverse(["1", "abc"], ParseInt)
    assert result.IsEmpty()
 
def test_partition_returns_values_and_empty_count():
    values, emptyCount = Partition([Option.Some(1), Option.Empty(), Option.Some(3)])
    assert values == [1, 3]
    assert emptyCount == 1
 
def test_choose_keeps_only_successful_conversions():
    values = Choose(["1", "abc", "3"], ParseInt)
    assert values == [1, 3]
