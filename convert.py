from __future__ import annotations

from .option.option import Option
from .result.result import Result


def OptionToResult[T](option: Option[T], error: Exception) -> Result[T]:
    return option.Match(Result.Success, lambda: Result.Fail(error))

def ResultToOption[T](result: Result[T]) -> Option[T]:
    return result.Match(Option.Some, lambda _: Option.Empty())
