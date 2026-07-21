import os
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from modules.user_activity.infrastructure.repositories.postgres_repository import (
    UserActivityRepository,
)

auth_scheme = APIKeyHeader(
    name="Authorization",
    description="Usa el formato: `Token <tu_token>`",
    auto_error=False,
)


def get_user_repo():
    return UserActivityRepository()


def get_current_user(
    authorization: str = Security(auth_scheme),
    repo: UserActivityRepository = Depends(get_user_repo),
):
    if not authorization or not authorization.lower().startswith("token "):
        raise HTTPException(status_code=401, detail="Falta header Authorization: Token <token>")
    token = authorization.split(" ", 1)[1]
    user = repo.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido")
    return user


def ensure_admin(user: dict):
    if user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Requiere rol admin")


def ensure_superadmin(user: dict):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Requiere rol superadmin")


def ensure_superadmin_token(token: Optional[str]):
    expected = os.getenv("SUPERADMIN_TOKEN")
    if not expected or not token or token != expected:
        raise HTTPException(status_code=403, detail="Token de superadmin inválido")
