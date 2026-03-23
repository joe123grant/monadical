from __future__ import annotations

from .result import Result


class HttpError(Exception):
    def __init__(self, statusCode: int, message: str = "") -> None:
        self.statusCode = statusCode
        super().__init__(f"HTTP {statusCode}" + (f": {message}" if message else ""))

def FromStatusCode[T](statusCode: int, body: T, message: str = "") -> Result[T]:
    if 200 <= statusCode < 300:
        return Result.Success(body)
    return Result.Fail(HttpError(statusCode, message))
