from __future__ import annotations

from collections.abc import Callable, Iterable

from .state import State

def Sequence[S, A](states: Iterable[State[S, A]]) -> State[S, list[A]]:
    def _Run(initialState: S) -> tuple[list[A], S]:
        values: list[A] = []
        current = initialState
        for state in states:
            value, current = state.Run(current)
            values.append(value)
        return values, current
    return State(_Run)

def Traverse[S, A, B](items: Iterable[A], func: Callable[[A], State[S, B]]) -> State[S, list[B]]:
    return Sequence(func(item) for item in items)

def Replicate[S, A](times: int, state: State[S, A]) -> State[S, list[A]]:
    return state.Replicate(times)
