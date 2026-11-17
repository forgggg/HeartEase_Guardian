from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    hint: str = ""


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, hint: str = "") -> None:
        self.status = status
        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(message)


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=ErrorResponse(
                code=exc.code, message=exc.message, hint=exc.hint
            ).model_dump(),
        )


def error_responses(*codes: int) -> dict[int, dict]:
    return {
        code: {"model": ErrorResponse, "description": f"HTTP {code}"} for code in codes
    }
