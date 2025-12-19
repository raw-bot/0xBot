"""Error handling middleware for consistent error responses."""

import traceback
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and format all exceptions.
    
    Provides consistent error responses across the API.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and catch exceptions.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response or error response
        """
        try:
            response = await call_next(request)
            return response
            
        except ValueError as e:
            # Validation errors
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "ValidationError",
                    "message": str(e),
                    "details": {}
                }
            )
            
        except PermissionError as e:
            # Permission denied
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "PermissionDenied",
                    "message": str(e),
                    "details": {}
                }
            )
            
        except FileNotFoundError as e:
            # Resource not found
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "NotFound",
                    "message": str(e),
                    "details": {}
                }
            )
            
        except Exception as e:
            # Catch-all for unexpected errors
            error_message = str(e)
            error_type = type(e).__name__
            
            # Log the error (in production, use proper logging)
            print(f"❌ Unhandled exception: {error_type}: {error_message}")
            print(traceback.format_exc())
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": error_type,
                    "message": "An internal server error occurred",
                    "details": {
                        "error": error_message if request.app.debug else "Internal server error"
                    }
                }
            )


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: dict = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error_type: Type of error (e.g., "ValidationError")
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional details
        
    Returns:
        JSONResponse with error information
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "message": message,
            "details": details or {}
        }
    )