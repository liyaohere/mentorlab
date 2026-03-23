"""Simple admin authentication via API key header.

Admin panel sends `X-Admin-Key: <key>` header with every request.
The key is set in .env as ADMIN_API_KEY. Simple and secure enough for a research tool.
"""
from fastapi import Depends, HTTPException, Query, Request, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin(
    request: Request,
    api_key: str | None = Security(api_key_header),
):
    """Dependency that validates the admin API key via header or query param.

    Supports ?admin_key=... for download links (<a> tags can't set headers).
    """
    if not settings.ADMIN_API_KEY:
        return True
    # Check header first, then query param fallback
    key = api_key or request.query_params.get("admin_key")
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )
    return True
