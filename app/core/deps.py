"""Kiểm tra đăng nhập + vai trò. Dùng: Depends(require_roles("admin", "manager"))"""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)  # hiện nút Authorize trong /docs


def get_current_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    try:
        return decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")


def require_roles(*roles: str):
    def checker(payload: dict = Depends(get_current_payload)) -> dict:
        if payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này")
        return payload

    return checker