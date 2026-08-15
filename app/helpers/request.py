from fastapi import Request


def get_client_ip_from_request(request: Request) -> str | None:
    """Получение IP адреса клиента из запроса FastAPI"""
    ip_address = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    return ip_address.split(",")[0] if ip_address else ip_address


def get_client_user_agent_from_request(request: Request) -> str | None:
    """Получение User-Agent клиента из запроса FastAPI"""
    return request.headers.get("user-agent")
