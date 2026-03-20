"""Simple admin authentication via API key header.

Admin panel sends `X-Admin-Key: <key>` header with every request.
The key is set in .env as ADMIN_API_KEY. Simple and secure enough for a research tool.
"""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin(api_key: str | None = Security(api_key_header)):
    """Dependency that validates the admin API key."""
    if not settings.ADMIN_API_KEY:
        # If no key configured, allow access (development mode)
        return True
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )
    return True
