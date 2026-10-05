from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions.base import (
    BusinessRuleViolation,
    DomainException,
    ExternalServiceError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

_STATUS = (
    (ExternalServiceError, 503, "service_unavailable"),
    (NotFoundError, 404, "not_found"),
    (PermissionDeniedError, 403, "forbidden"),
    (ValidationError, 422, "validation_error"),
    (BusinessRuleViolation, 409, "business_rule_violation"),
    (DomainException, 400, "domain_error"),
)


def error_body(code: str, message: str, details: object | None = None) -> dict:
    return {"code": code, "message": message, "details": details}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    async def _domain(_: Request, exc: DomainException) -> JSONResponse:
        for cls, status, code in _STATUS:
            if isinstance(exc, cls):
                return JSONResponse(status_code=status, content=error_body(code, str(exc)))
        raise exc  # unreachable: DomainException is the last entry


_HTTP_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
               405: "method_not_allowed", 409: "conflict", 429: "rate_limited"}


def register_http_error_handlers(app: FastAPI) -> None:
    """Make framework-generated errors follow the same {code, message, details} shape."""

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})
        return JSONResponse(
            status_code=422, content=error_body("validation_error", "Invalid request", details)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        headers = getattr(exc, "headers", None)
        return JSONResponse(
            status_code=exc.status_code, content=error_body(code, str(exc.detail)), headers=headers
        )

    @app.exception_handler(PydanticValidationError)
    async def _pydantic(_: Request, exc: PydanticValidationError) -> JSONResponse:
        # Safety net: a shared application DTO rejected a value the request schema let through.
        details = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})
        return JSONResponse(
            status_code=422, content=error_body("validation_error", "Invalid value", details)
        )
