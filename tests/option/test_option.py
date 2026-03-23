from __future__ import annotations
 
import pytest
 
from dscoe_func.option.option import Option, Some
from dscoe_func.option.parse import ParseInt
 
def test_some_is_truthy_and_not_empty():
    option = Option.Some(42)
    assert option.IsSome()
    assert not option.IsEmpty()
    assert bool(option) is True
 
def test_empty_is_falsy_and_not_some():
    option = Option.Empty()
    assert option.IsEmpty()
    assert not option.IsSome()
    assert bool(option) is False
 
def test_empty_is_a_singleton():
    assert Option.Empty() is Option.Empty()
 
def test_some_is_frozen():
    option = Option.Some(42)
    with pytest.raises(AttributeError):
        option.value = 99
 
def test_repr_for_some():
    assert repr(Option.Some(42)) == "Some(42)"
 
def test_repr_for_empty():
    assert repr(Option.Empty()) == "Empty()"
 
def test_some_equality_uses_wrapped_value():
    assert Option.Some(1) == Option.Some(1)
    assert Option.Some(1) != Option.Some(2)
 
def test_empty_equality_matches_empty():
    assert Option.Empty() == Option.Empty()
    assert Option.Some(1) != Option.Empty()
 
def test_option_is_hashable():
    options = {Option.Some(1), Option.Some(1), Option.Empty(), Option.Empty()}
    assert options == {Option.Some(1), Option.Empty()}
 
def test_iter_on_some_yields_value():
    assert list(Option.Some(5)) == [5]
 
def test_iter_on_empty_yields_nothing():
    assert list(Option.Empty()) == []
 
def test_or_operator_keeps_left_some():
    result = Option.Some(1) | Option.Some(2)
    assert result == Option.Some(1)
 
def test_or_operator_uses_right_when_left_is_empty():
    result = Option.Empty() | Option.Some(2)
    assert result == Option.Some(2)
 
def test_or_operator_is_lazy_for_empty():
    wasCalled = False
 
    def factory():
        nonlocal wasCalled
        wasCalled = True
        return Option.Some(3)
 
    result = Option.Empty() | factory
 
    assert wasCalled is True
    assert result == Option.Some(3)
 
def test_bind_operator_maps_some_value():
    result = Option.Some(1) >> (lambda value: Option.Some(value + 1))
    assert result == Option.Some(2)
 
def test_bind_operator_short_circuits_on_empty():
    result = Option.Empty() >> (lambda value: Option.Some(value + 1))
    assert result.IsEmpty()
 
def test_map_transforms_some_value():
    result = Option.Some(2).Map(lambda value: value * 3)
    assert result == Option.Some(6)
 
def test_map_on_empty_returns_empty():
    result = Option.Empty().Map(lambda value: value * 3)
    assert result.IsEmpty()
 
def test_bimap_uses_some_mapper_for_some():
    result = Option.Some(5).BiMap(lambda value: value + 1, lambda: 0)
    assert result == Option.Some(6)
 
def test_bimap_uses_empty_mapper_for_empty():
    result = Option.Empty().BiMap(lambda value: value + 1, lambda: 0)
    assert result == Option.Some(0)
 
def test_bind_supports_chaining():
    result = Option.Some("42") >> ParseInt
    assert result == Option.Some(42)
 
def test_filter_keeps_matching_value():
    result = Option.Some(4).Filter(lambda value: value > 2)
    assert result == Option.Some(4)
 
def test_filter_discards_non_matching_value():
    result = Option.Some(1).Filter(lambda value: value > 2)
    assert result.IsEmpty()
 
def test_filter_on_empty_returns_empty():
    result = Option.Empty().Filter(lambda value: value > 2)
    assert result.IsEmpty()
 
def test_from_nullable_returns_empty_for_none():
    assert Option.FromNullable(None).IsEmpty()
 
def test_from_nullable_wraps_zero():
    assert Option.FromNullable(0) == Option.Some(0)
 
def test_from_nullable_string_returns_empty_for_blank_after_strip():
    assert Option.FromNullableString(" ", strip=True).IsEmpty()
 
def test_from_dict_returns_some_for_existing_key():
    option = Option.FromDict({"a": 1}, "a")
    assert option == Option.Some(1)
 
def test_from_dict_returns_empty_for_missing_key():
    option = Option.FromDict({"a": 1}, "b")
    assert option.IsEmpty()
 
def test_from_bool_returns_some_when_true():
    assert Option.FromBool(True, 5) == Option.Some(5)
 
def test_from_bool_returns_empty_when_false():
    assert Option.FromBool(False, 5).IsEmpty()
 
def test_when_returns_some_when_condition_is_true():
    option = Option.When(True, lambda: 42)
    assert option == Option.Some(42)
 
def test_when_returns_empty_when_condition_is_false():
    option = Option.When(False, lambda: 42)
    assert option.IsEmpty()
 
def test_try_returns_some_when_function_succeeds():
    option = Option.Try(lambda: 42)
    assert option == Option.Some(42)
 
def test_try_returns_empty_when_function_raises_caught_exception():
    option = Option.Try(lambda: 1 / 0)
    assert option.IsEmpty()
 
def test_try_reraises_unlisted_exception_type():
    with pytest.raises(TypeError):
        Option.Try(lambda: (_ for _ in ()).throw(TypeError("bad type")), exceptions=ValueError)
 
def test_if_empty_returns_wrapped_value_when_some():
    value = Option.Some(1).IfEmpty(lambda: 99)
    assert value == 1
 
def test_if_empty_calls_factory_when_empty():
    value = Option.Empty().IfEmpty(lambda: 99)
    assert value == 99
 
def test_if_empty_value_returns_default_when_empty():
    value = Option.Empty().IfEmptyValue(99)
    assert value == 99
 
def test_unwrap_returns_value_for_some():
    assert Option.Some(1).Unwrap() == 1
 
def test_unwrap_raises_for_empty():
    with pytest.raises(ValueError):
        Option.Empty().Unwrap()
 
def test_exists_checks_wrapped_value():
    assert Option.Some(5).Exists(lambda value: value > 3) is True
    assert Option.Empty().Exists(lambda value: value > 3) is False
 
def test_for_all_is_true_for_empty():
    assert Option.Empty().ForAll(lambda value: value > 3) is True
 
def test_contains_checks_wrapped_value():
    assert Option.Some(5).Contains(5) is True
    assert Option.Some(5).Contains(6) is False
 
def test_count_is_one_for_some_and_zero_for_empty():
    assert Option.Some(5).Count() == 1
    assert Option.Empty().Count() == 0
 
def test_fold_accumulates_some_value():
    result = Option.Some(5).Fold(0, lambda state, value: state + value)
    assert result == 5
 
def test_fold_returns_seed_for_empty():
    result = Option.Empty().Fold(0, lambda state, value: state + value)
    assert result == 0
 
def test_bifold_uses_some_branch_for_some():
    result = Option.Some(5).BiFold(0, lambda state, value: state + value, lambda state: state - 1)
    assert result == 5
 
def test_bifold_uses_empty_branch_for_empty():
    result = Option.Empty().BiFold(0, lambda state, value: state + value, lambda state: state - 1)
    assert result == -1
 
def test_tap_runs_action_for_some_and_returns_self():
    seen = []
    option = Option.Some(5)
    result = option.Tap(lambda value: seen.append(value))
    assert seen == [5]
    assert result is option
 
def test_tap_empty_runs_action_for_empty_and_returns_self():
    seen = []
    option = Option.Empty()
    result = option.TapEmpty(lambda: seen.append("empty"))
    assert seen == ["empty"]
    assert result is option
 
def test_or_else_keeps_some():
    result = Option.Some(1).OrElse(lambda: Option.Some(2))
    assert result == Option.Some(1)
 
def test_or_else_uses_factory_for_empty():
    result = Option.Empty().OrElse(lambda: Option.Some(2))
    assert result == Option.Some(2)
 
def test_zip_returns_tuple_when_both_are_some():
    result = Option.Some(1).Zip(Option.Some(2))
    assert result == Option.Some((1, 2))
 
def test_zip_returns_empty_when_either_side_is_empty():
    result = Option.Some(1).Zip(Option.Empty())
    assert result.IsEmpty()
 
def test_map2_applies_function_when_both_are_some():
    result = Option.Some(2).Map2(Option.Some(3), lambda first, second: first + second)
    assert result == Option.Some(5)
 
def test_all_returns_some_tuple_when_all_present():
    result = Option.All(Option.Some(1), Option.Some(2), Option.Some(3))
    assert result == Option.Some((1, 2, 3))
 
def test_all_returns_empty_when_any_value_is_missing():
    result = Option.All(Option.Some(1), Option.Empty(), Option.Some(3))
    assert result.IsEmpty()
 
def test_all_with_no_arguments_returns_empty_tuple_in_some():
    result = Option.All()
    assert result == Option.Some(())
 
def test_zip_n_delegates_to_all():
    result = Option.ZipN(Option.Some(1), Option.Some(2))
    assert result == Option.Some((1, 2))
 
def test_map_n_unpacks_values_into_function():
    result = Option.MapN(lambda first, second, third: first + second + third, Option.Some(1), Option.Some(2), Option.Some(3))
    assert result == Option.Some(6)
 
def test_flatten_removes_one_layer_of_option():
    result = Option.Some(Option.Some(3)).Flatten()
    assert result == Option.Some(3)
 
def test_flatten_preserves_empty_inner_option():
    result = Option.Some(Option.Empty()).Flatten()
    assert result.IsEmpty()
 
def test_to_list_returns_single_item_for_some():
    assert Option.Some(1).ToList() == [1]
 
def test_to_list_returns_empty_list_for_empty():
    assert Option.Empty().ToList() == []
 
def test_to_nullable_returns_value_for_some():
    assert Option.Some(1).ToNullable() == 1
 
def test_to_nullable_returns_none_for_empty():
    assert Option.Empty().ToNullable() is None
 
@pytest.mark.asyncio
async def test_map_async_transforms_some_value():
    async def mapper(value):
        return value + 1
 
    result = await Option.Some(1).MapAsync(mapper)
    assert result == Option.Some(2)
 
@pytest.mark.asyncio
async def test_map_async_short_circuits_for_empty():
    wasCalled = False
 
    async def mapper(value):
        nonlocal wasCalled
        wasCalled = True
        return value + 1
 
    result = await Option.Empty().MapAsync(mapper)
    assert result.IsEmpty()
    assert wasCalled is False
 
@pytest.mark.asyncio
async def test_bind_async_transforms_some_value():
    async def binder(value):
        return Option.Some(value + 1)
 
    result = await Option.Some(1).BindAsync(binder)
    assert result == Option.Some(2)
 
@pytest.mark.asyncio
async def test_bind_async_short_circuits_for_empty():
    wasCalled = False
 
    async def binder(value):
        nonlocal wasCalled
        wasCalled = True
        return Option.Some(value + 1)
 
    result = await Option.Empty().BindAsync(binder)
    assert result.IsEmpty()
    assert wasCalled is False
 
@pytest.mark.asyncio
async def test_match_async_uses_some_branch():
    async def whenSome(value):
        return value + 1
 
    async def whenEmpty():
        return 0
 
    result = await Option.Some(1).MatchAsync(whenSome, whenEmpty)
    assert result == 2
 
@pytest.mark.asyncio
async def test_match_async_uses_empty_branch():
    async def whenSome(value):
        return value + 1
 
    async def whenEmpty():
        return 0
 
    result = await Option.Empty().MatchAsync(whenSome, whenEmpty)
    assert result == 0
 
def test_bind_left_identity_law():
    function = lambda value: Option.Some(value + 1)
    assert Option.Some(5).Bind(function) == function(5)
 
def test_bind_right_identity_law_for_some():
    option = Option.Some(5)
    assert option.Bind(Option.Some) == option
 
def test_bind_right_identity_law_for_empty():
    option = Option.Empty()
    assert option.Bind(Option.Some) == option
 
def test_bind_associativity_law():
    option = Option.Some(5)
    first = lambda value: Option.Some(value + 2)
    second = lambda value: Option.Some(value * 3)
 
    left = option.Bind(first).Bind(second)
    right = option.Bind(lambda value: first(value).Bind(second))
 
    assert left == right
