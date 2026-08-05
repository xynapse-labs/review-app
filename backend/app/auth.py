import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# Minimal in-memory session store: token -> user_id.
# This is intentionally simple (no JWT, no hashing) per the project's
# explicit scope: hardcoded demo users, not production auth.
_SESSIONS: dict[str, int] = {}

_auth_header = APIKeyHeader(name="Authorization", auto_error=False)


def create_session(user_id: int) -> str:
    token = secrets.token_hex(16)
    _SESSIONS[token] = user_id
    return token


def get_current_user(
    authorization: str | None = Depends(_auth_header),
    db: Session = Depends(get_db),
) -> models.User:
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = _SESSIONS.get(token)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_role(role: models.Role):
    def _check(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role={role.value}")
        return user

    return _check
