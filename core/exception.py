import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

error_logger = logging.getLogger("django.error")


def custom_exception_handler(
        exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Centralized exception handler ensure all error return structured JSON"""
    #Call DRF's standard exception handler first to handle standard API exception
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None

    if response is not None:
        response.data = {
            "error": "client_error",
            "message": response.data,
            "request_id": request_id
        }
        return response

    # If response is not None, then it is an uncaught insternal server crash(HTTP 500)
    path = request.path if request else "unknown"

    error_logger.error(
        "unhandled_server_exception",
        exc_info=exc,
        extra={
            "request_id": request_id,
            "path": path,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
    )

    return Response(
        {
            "error": "internal_server_error",
            "message": "An unexpected error occured. Please try again later.",
            "request_id": request_id
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
