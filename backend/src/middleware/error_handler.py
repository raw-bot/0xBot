import traceback
from typing import Any, Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

ERROR_MAPPINGS = {
    ValueError: (status.HTTP_400_BAD_REQUEST, "ValidationError"),
    PermissionError: (status.HTTP_403_FORBIDDEN, "PermissionDenied"),
    FileNotFoundError: (status.HTTP_404_NOT_FOUND, "NotFound"),
}


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: dict[str, Any] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error_type, "message": message, "details": details or {}}
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            error_type = type(e)

            if error_type in ERROR_MAPPINGS:
                status_code, error_name = ERROR_MAPPINGS[error_type]
                return create_error_response(error_name, str(e), status_code)

            print(f"Unhandled exception: {error_type.__name__}: {e}")
            print(traceback.format_exc())

            message = str(e) if getattr(request.app, "debug", False) else "Internal server error"
            return create_error_response(
                error_type.__name__,
                "An internal server error occurred",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": message}
            )
