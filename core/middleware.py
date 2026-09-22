import logging
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

access_logger = logging.getLogger('app.access')

class RequestContextMiddleware:
    """Attached a unique X-Request-ID and emits structured access log ."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = str(uuid.uuid4())
        #Attach the request for view access
        request.request_id = request_id  # type: ignore[attr-defined]
        start_time = time.perf_counter()

        response = self.get_response(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        #Emit structured log
        access_logger.info(
            "request_handled",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }
        )
        response["X-Request-ID"] = request_id
        return response
