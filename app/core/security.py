"""Mã hoá mật khẩu (bcrypt) và tạo / kiểm tra token đăng nhập (JWT).

- access token: sống ngắn (mặc định 30 phút), gửi kèm mỗi request: Authorization: Bearer <token>
- refresh token: sống dài (mặc định 7 ngày), chỉ dùng để xin access token mới
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import uuid

from app.core.config import settings


# ---------- Mật khẩu ----------
def _to_bytes(password: str) -> bytes:
    # bcrypt chỉ đọc tối đa 72 byte đầu của mật khẩu
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """Mật khẩu chữ thường -> chuỗi bcrypt để lưu vào users.password_hash."""
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except ValueError:  # password_hash không phải chuỗi bcrypt hợp lệ
        return False


# ---------- Token ----------
def _create_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    payload = {
        **data,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: dict) -> str:
    return _create_token(data, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(data: dict) -> str:
    return _create_token(data, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, token_type: str) -> dict:
    """Giải mã token. Sai chữ ký, hết hạn hoặc sai loại (access/refresh) -> ném jwt.InvalidTokenError."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError("Sai loại token")
    return payload