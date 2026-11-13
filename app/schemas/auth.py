"""Schema cho đăng nhập và làm mới token."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(examples=["admin@restaurant.com"])
    password: str = Field(examples=["Restaurant@123"])


class TokenOut(BaseModel):
    """Trả về sau khi đăng nhập thành công."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenOut(BaseModel):
    """Trả về sau khi làm mới token."""

    access_token: str
    token_type: str = "bearer"
    
class LogoutRequest(BaseModel):
    refresh_token: str