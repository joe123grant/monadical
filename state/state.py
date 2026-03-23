from __future__ import annotations

from collections.abc import Callable


class State[S, A]:
    def __init__(self, run: Callable[[S], tuple[A, S]]) -> None:
        self._run = run

    @staticmethod
    def Of(value: A) -> State[S, A]:
        return State(lambda state: (value, state))

    @staticmethod
    def Get() -> State[S, S]:
        return State(lambda state: (state, state))

    @staticmethod
    def Put(state: S) -> State[S, None]:
        return State(lambda _: (None, state))

    @staticmethod
    def Modify(func: Callable[[S], S]) -> State[S, None]:
        return State(lambda state: (None, func(state)))

    @staticmethod
    def Gets(func: Callable[[S], A]) -> State[S, A]:
        return State(lambda state: (func(state), state))

    @staticmethod
    def When(predicate: Callable[[S], bool], action: State[S, None]) -> State[S, None]:
        def _Run(state: S) -> tuple[None, S]:
            if predicate(state):
                return action.Run(state)
            return None, state
        return State(_Run)

    def Run(self, initial: S) -> tuple[A, S]:
        return self._run(initial)

    def Eval(self, initial: S) -> A:
        return self._run(initial)[0]

    def Exec(self, initial: S) -> S:
        return self._run(initial)[1]

    def ToResult(self, initial: S) -> Result[tuple[A, S]]:
        from ..result.result import Result
        try:
            return Result.Success(self._run(initial))
        except Exception as exception:
            return Result.Fail(exception)

    def __repr__(self) -> str:
        return "State(...)"

    def __rshift__[B](self, func: Callable[[A], State[S, B]]) -> State[S, B]:
        return self.Bind(func)

    def Map[B](self, func: Callable[[A], B]) -> State[S, B]:
        def _Run(state: S) -> tuple[B, S]:
            value, nextState = self._run(state)
            return func(value), nextState
        return State(_Run)

    def Bind[B](self, func: Callable[[A], State[S, B]]) -> State[S, B]:
        def _Run(state: S) -> tuple[B, S]:
            value, nextState = self._run(state)
            return func(value).Run(nextState)
        return State(_Run)

    def Then[B](self, other: State[S, B]) -> State[S, B]:
        return self.Bind(lambda _: other)

    def Flatten(self: State[S, State[S, A]]) -> State[S, A]:
        return self.Bind(lambda inner: inner)

    def Zip[B](self, other: State[S, B]) -> State[S, tuple[A, B]]:
        return self.Bind(lambda first: other.Map(lambda second: (first, second)))

    def Map2[B, C](self, other: State[S, B], func: Callable[[A, B], C]) -> State[S, C]:
        return self.Zip(other).Map(lambda pair: func(pair[0], pair[1]))

    def Fold[B](self, initial: B, folder: Callable[[B, A], B]) -> State[S, B]:
        return self.Map(lambda value: folder(initial, value))

    def BiFold[B](self, initial: B, valueFolder: Callable[[B, A], B], stateFolder: Callable[[B, S], B]) -> State[S, B]:
        def _Run(state: S) -> tuple[B, S]:
            value, nextState = self._run(state)
            folded = valueFolder(initial, value)
            return stateFolder(folded, nextState), nextState
        return State(_Run)

    def Exists(self, predicate: Callable[[A], bool]) -> State[S, bool]:
        return self.Map(predicate)

    def ForAll(self, predicate: Callable[[A], bool]) -> State[S, bool]:
        return self.Map(predicate)

    def TryMap[B](self, func: Callable[[A], B]) -> State[S, Result[B]]:
        from ..result.result import Result
        def _Run(state: S) -> tuple[Result[B], S]:
            value, nextState = self._run(state)
            try:
                return Result.Success(func(value)), nextState
            except Exception as exception:
                return Result.Fail(exception), nextState
        return State(_Run)

    def Local(self, func: Callable[[S], S]) -> State[S, A]:
        def _Run(state: S) -> tuple[A, S]:
            value, _ = self._run(func(state))
            return value, state
        return State(_Run)

    def Zoom[BigS](self, getter: Callable[[BigS], S], setter: Callable[[BigS, S], BigS]) -> State[BigS, A]:
        def _Run(bigState: BigS) -> tuple[A, BigS]:
            value, newSmallState = self._run(getter(bigState))
            return value, setter(bigState, newSmallState)
        return State(_Run)

    def Inspect[B](self, func: Callable[[S], B]) -> State[S, B]:
        def _Run(state: S) -> tuple[B, S]:
            _, nextState = self._run(state)
            return func(nextState), nextState
        return State(_Run)

    def BiMap[B](self, valueFunc: Callable[[A], B], stateFunc: Callable[[S], S]) -> State[S, B]:
        def _Run(state: S) -> tuple[B, S]:
            value, nextState = self._run(state)
            return valueFunc(value), stateFunc(nextState)
        return State(_Run)

    def Tap(self, action: Callable[[A], None]) -> State[S, A]:
        def _Run(state: S) -> tuple[A, S]:
            value, nextState = self._run(state)
            action(value)
            return value, nextState
        return State(_Run)

    def TapState(self, action: Callable[[S], None]) -> State[S, A]:
        def _Run(state: S) -> tuple[A, S]:
            value, nextState = self._run(state)
            action(nextState)
            return value, nextState
        return State(_Run)

    def Replicate(self, times: int) -> State[S, list[A]]:
        def _Run(state: S) -> tuple[list[A], S]:
            values: list[A] = []
            current = state
            for _ in range(times):
                value, current = self._run(current)
                values.append(value)
            return values, current
        return State(_Run)
