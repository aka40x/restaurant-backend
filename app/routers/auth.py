"""API đăng nhập. Đường dẫn đầy đủ: /api/auth

    POST /api/auth/login     đăng nhập bằng email + mật khẩu -> access token + refresh token
    POST /api/auth/refresh   gửi refresh token -> access token mới
"""
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core import login_limiter
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, password_fingerprint, verify_password,
)
from app.crud import user as user_crud
from app.crud import revoked_token as revoked_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenOut, ChangePasswordRequest, LoginRequest, LogoutRequest, RefreshRequest, TokenOut
from app.core.deps import bearer_scheme, get_current_user
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _access_token_for(user: User) -> str:
    return create_access_token({
        "sub": str(user.id), "role": user.role.name, "branch_id": user.branch_id,
        "pwd": password_fingerprint(user.password_hash),
    })


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    login_limiter.check(email)  # sai quá 5 lần / 15 phút -> 429
    user = user_crud.get_user_by_email(db, email)
    # Sai email hay sai mật khẩu đều trả CÙNG một câu, không cho kẻ xấu biết email nào tồn tại
    if user is None or not verify_password(data.password, user.password_hash):
        login_limiter.record_failure(email)
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khoá")
    login_limiter.reset(email)

    return TokenOut(
        access_token=_access_token_for(user),
        refresh_token=create_refresh_token({"sub": str(user.id), "pwd": password_fingerprint(user.password_hash)}),
    )


@router.post("/refresh", response_model=AccessTokenOut)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token, "refresh")
    except jwt.InvalidTokenError:  # hết hạn, sai chữ ký, hoặc gửi nhầm access token
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ hoặc đã hết hạn")
    if revoked_crud.is_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=401, detail="Refresh token đã bị thu hồi")

    user = user_crud.get_user(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại hoặc đã bị khoá")
    if payload.get("pwd") != password_fingerprint(user.password_hash):
        raise HTTPException(status_code=401, detail="Mật khẩu đã thay đổi, vui lòng đăng nhập lại")

    return AccessTokenOut(access_token=_access_token_for(user))
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@router.post("/logout", status_code=204)
def logout(data: LogoutRequest, credentials=Depends(bearer_scheme), db: Session = Depends(get_db)):
    pairs = [(data.refresh_token, "refresh")]
    if credentials is not None:
        pairs.append((credentials.credentials, "access"))
    for token, token_type in pairs:
        try:
            payload = decode_token(token, token_type)
        except jwt.InvalidTokenError:
            continue
        revoked_crud.revoke(db, payload["jti"], payload["exp"])
    revoked_crud.purge_expired(db)
    return Response(status_code=204)

@router.post("/change-password", status_code=204)
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        # cố ý dùng 400 chứ không phải 401, để FE không tưởng là hết phiên rồi tự đăng xuất
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")
    if not data.new_password.strip():
        raise HTTPException(status_code=400, detail="Mật khẩu mới không được chỉ gồm khoảng trắng")
    if data.new_password == data.current_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải khác mật khẩu hiện tại")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return Response(status_code=204)