"""Bearer authorization for control operations."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param


def require_operator(request: Request) -> str:
    expected: str | None = request.app.state.settings.api_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="operator authentication is not configured",
        )
    scheme, supplied = get_authorization_scheme_param(request.headers.get("Authorization", ""))
    if scheme.lower() != "bearer" or not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="operator authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "local-operator"
