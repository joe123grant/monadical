from __future__ import annotations

from .result import Result

class HttpError(Exception):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}" + (f": {message}" if message else ""))

def FromStatusCode[T](status_code: int, body: T, message: str = "") -> Result[T]:
    if 200 <= status_code < 300:
        return Result.Success(body)
    return Result.Fail(HttpError(status_code, message))
