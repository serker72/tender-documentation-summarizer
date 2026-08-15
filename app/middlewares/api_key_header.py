from typing import List, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class ApiKeyHeaderMiddleware(BaseHTTPMiddleware):
    """Проверка значения APIKey в заголовке запроса"""

    def __init__(
        self, app, key_value: str, header_name: str = "X-Api-Key", ignored_endpoints: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.header_name = header_name
        self.key_value = key_value
        self.ignored_endpoints = ignored_endpoints or []

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.ignored_endpoints:
            return await call_next(request)

        header_value = request.headers.get(self.header_name)
        if not header_value or header_value != self.key_value:
            response = JSONResponse(
                content=f"API key {'not found' if not header_value else 'value is incorrect'}",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            response = await call_next(request)

        return response
