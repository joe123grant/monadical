from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .state import State


def Sequence(states: Iterable[State[Any, Any]]) -> State[Any, list[Any]]:
    def _run(s: Any) -> tuple[list[Any], Any]:
        values: list[Any] = []
        current = s
        for state in states:
            a, current = state.Run(current)
            values.append(a)
        return values, current
    return State(_run)


def Traverse(items: Iterable[Any], func: Callable[[Any], State[Any, Any]]) -> State[Any, list[Any]]:
    return Sequence(func(item) for item in items)


def Replicate(times: int, state: State[Any, Any]) -> State[Any, list[Any]]:
    def _run(s: Any) -> tuple[list[Any], Any]:
        values: list[Any] = []
        current = s
        for _ in range(times):
            a, current = state.Run(current)
            values.append(a)
        return values, current
    return State(_run)
