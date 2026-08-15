import time
from uuid import uuid4

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.helpers.request import get_client_ip_from_request, get_client_user_agent_from_request

logger = structlog.stdlib.get_logger()


class RequestProcessingTimeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Process-Time"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        request_id = request.headers.get("x-request-id") or uuid4().hex
        user_ip = get_client_ip_from_request(request)
        user_agent = get_client_user_agent_from_request(request)

        # Привязываем контекст — все логи внутри запроса получат эти поля
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=user_ip,
            client_user_agent=user_agent,
        )

        try:
            request.state.request_id = request_id
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            await logger.ainfo(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            response.headers["X-Request-ID"] = request_id
            response.headers[self.header_name] = "{0:.2f}".format(duration_ms)

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await logger.aerror(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
            )

            raise
