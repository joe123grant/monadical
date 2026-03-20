from __future__ import annotations

from collections.abc import Callable


class State[S, A]:
    def __init__(self, run: Callable[[S], tuple[A, S]]) -> None:
        self._run = run

    @staticmethod
    def Of(value: A) -> State[S, A]:
        return State(lambda s: (value, s))

    @staticmethod
    def Get() -> State[S, S]:
        return State(lambda s: (s, s))

    @staticmethod
    def Put(state: S) -> State[S, None]:
        return State(lambda _: (None, state))

    @staticmethod
    def Modify(func: Callable[[S], S]) -> State[S, None]:
        return State(lambda s: (None, func(s)))

    @staticmethod
    def Gets(func: Callable[[S], A]) -> State[S, A]:
        return State(lambda s: (func(s), s))

    @staticmethod
    def When(predicate: Callable[[S], bool], action: State[S, None]) -> State[S, None]:
        def _run(s: S) -> tuple[None, S]:
            if predicate(s):
                return action.Run(s)
            return None, s
        return State(_run)

    def Run(self, initial: S) -> tuple[A, S]:
        return self._run(initial)

    def Eval(self, initial: S) -> A:
        return self._run(initial)[0]

    def Exec(self, initial: S) -> S:
        return self._run(initial)[1]

    def ToResult(self, initial: S):
        from ..result.result import Result
        try:
            return Result.Success(self._run(initial))
        except Exception as ex:
            return Result.Fail(ex)

    def __repr__(self) -> str:
        return "State(...)"

    def __rshift__[B](self, func: Callable[[A], State[S, B]]) -> State[S, B]:
        return self.Bind(func)

    def Map[B](self, func: Callable[[A], B]) -> State[S, B]:
        def _run(s: S) -> tuple[B, S]:
            a, s2 = self._run(s)
            return func(a), s2
        return State(_run)

    def Bind[B](self, func: Callable[[A], State[S, B]]) -> State[S, B]:
        def _run(s: S) -> tuple[B, S]:
            a, s2 = self._run(s)
            return func(a).Run(s2)
        return State(_run)

    def Then[B](self, other: State[S, B]) -> State[S, B]:
        return self.Bind(lambda _: other)

    def Flatten(self: State[S, State[S, A]]) -> State[S, A]:
        return self.Bind(lambda inner: inner)

    def Zip[B](self, other: State[S, B]) -> State[S, tuple[A, B]]:
        return self.Bind(lambda a: other.Map(lambda b: (a, b)))

    def Map2[B, C](self, other: State[S, B], func: Callable[[A, B], C]) -> State[S, C]:
        return self.Zip(other).Map(lambda t: func(t[0], t[1]))

    def Fold[B](self, initial: B, folder: Callable[[B, A], B]) -> State[S, B]:
        return self.Map(lambda a: folder(initial, a))

    def BiFold[B](self, initial: B, valueFolder: Callable[[B, A], B], stateFolder: Callable[[B, S], B]) -> State[S, B]:
        def _run(s: S) -> tuple[B, S]:
            a, s2 = self._run(s)
            b = valueFolder(initial, a)
            return stateFolder(b, s2), s2
        return State(_run)

    def Exists(self, predicate: Callable[[A], bool]) -> State[S, bool]:
        return self.Map(predicate)

    def ForAll(self, predicate: Callable[[A], bool]) -> State[S, bool]:
        return self.Map(predicate)

    def TryMap[B](self, func: Callable[[A], B]) -> State[S, object]:
        from ..result.result import Result
        def _run(s: S) -> tuple[object, S]:
            a, s2 = self._run(s)
            try:
                return Result.Success(func(a)), s2
            except Exception as ex:
                return Result.Fail(ex), s2
        return State(_run)

    def Local(self, func: Callable[[S], S]) -> State[S, A]:
        def _run(s: S) -> tuple[A, S]:
            a, _ = self._run(func(s))
            return a, s
        return State(_run)

    def Zoom[BigS](self, getter: Callable[[BigS], S], setter: Callable[[BigS, S], BigS]) -> State[BigS, A]:
        def _run(big_s: BigS) -> tuple[A, BigS]:
            a, new_small_s = self._run(getter(big_s))
            return a, setter(big_s, new_small_s)
        return State(_run)

    def Inspect[B](self, func: Callable[[S], B]) -> State[S, B]:
        def _run(s: S) -> tuple[B, S]:
            _, s2 = self._run(s)
            return func(s2), s2
        return State(_run)

    def BiMap[B](self, valueFunc: Callable[[A], B], stateFunc: Callable[[S], S]) -> State[S, B]:
        def _run(s: S) -> tuple[B, S]:
            a, s2 = self._run(s)
            return valueFunc(a), stateFunc(s2)
        return State(_run)

    def Tap(self, action: Callable[[A], None]) -> State[S, A]:
        def _run(s: S) -> tuple[A, S]:
            a, s2 = self._run(s)
            action(a)
            return a, s2
        return State(_run)

    def TapState(self, action: Callable[[S], None]) -> State[S, A]:
        def _run(s: S) -> tuple[A, S]:
            a, s2 = self._run(s)
            action(s2)
            return a, s2
        return State(_run)

    def Replicate(self, times: int) -> State[S, list[A]]:
        def _run(s: S) -> tuple[list[A], S]:
            values: list[A] = []
            current = s
            for _ in range(times):
                a, current = self._run(current)
                values.append(a)
            return values, current
        return State(_run)
