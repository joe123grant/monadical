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

    def Run(self, initial: S) -> tuple[A, S]:
        return self._run(initial)

    def Eval(self, initial: S) -> A:
        return self._run(initial)[0]

    def Exec(self, initial: S) -> S:
        return self._run(initial)[1]

    def __repr__(self) -> str:
        return "State(...)"

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

    def Local(self, func: Callable[[S], S]) -> State[S, A]:
        def _run(s: S) -> tuple[A, S]:
            a, _ = self._run(func(s))
            return a, s
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
