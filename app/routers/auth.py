"""API đăng nhập. Đường dẫn đầy đủ: /api/auth

    POST /api/auth/login     đăng nhập bằng email + mật khẩu -> access token + refresh token
    POST /api/auth/refresh   gửi refresh token -> access token mới
"""
import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenOut, LoginRequest, RefreshRequest, TokenOut
from app.core.deps import get_current_user
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _access_token_for(user: User) -> str:
    # Nhét sẵn vai trò và chi nhánh vào token để các API khác kiểm tra quyền không phải hỏi lại DB
    return create_access_token({"sub": str(user.id), "role": user.role.name, "branch_id": user.branch_id})


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = user_crud.get_user_by_email(db, data.email.strip().lower())
    # Sai email hay sai mật khẩu đều trả CÙNG một câu, không cho kẻ xấu biết email nào tồn tại
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khoá")

    return TokenOut(
        access_token=_access_token_for(user),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/refresh", response_model=AccessTokenOut)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token, "refresh")
    except jwt.InvalidTokenError:  # hết hạn, sai chữ ký, hoặc gửi nhầm access token
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ hoặc đã hết hạn")

    user = user_crud.get_user(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại hoặc đã bị khoá")

    return AccessTokenOut(access_token=_access_token_for(user))
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user