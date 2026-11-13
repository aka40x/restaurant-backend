"""API thanh toán (M5). Đường dẫn đầy đủ: /api/payments

    GET /api/payments/bill/{order_id}   xem hoá đơn tạm của order (tạm tính, giảm giá, tổng).
                                        Gửi thêm ?voucher_code=WELCOME10 để áp voucher.

Quyền: cashier, manager (đúng chi nhánh của order) và admin (mọi chi nhánh).
"""
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.crud import bill as bill_crud
from app.crud.bill_rules import BillError
from app.db.session import get_db
from app.schemas.bill import BillOut
from app.crud import revoked_token as revoked_crud


router = APIRouter(prefix="/payments", tags=["Payments"])

bearer_scheme = HTTPBearer()  # hiện nút Authorize trong Swagger để dán access token
BILL_ROLES = {"admin", "manager", "cashier"}


def get_token_payload(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Đọc access token trong header Authorization. Token có sẵn: sub (id), role, branch_id."""
    try:
        return decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:  # hết hạn, sai chữ ký, hoặc gửi nhầm refresh token
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")


@router.get("/bill/{order_id}", response_model=BillOut)
def get_bill(
    order_id: int,
    voucher_code: str | None = None,
    claims: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
):
    role = claims.get("role")
    if role not in BILL_ROLES:
        raise HTTPException(status_code=403, detail="Chỉ thu ngân, quản lý hoặc admin mới xem được hoá đơn")

    # admin xem mọi chi nhánh; cashier/manager chỉ xem order của chi nhánh mình (BR-02)
    only_branch_id = None
    if role != "admin":
        only_branch_id = claims.get("branch_id")
        if only_branch_id is None:
            raise HTTPException(status_code=403, detail="Tài khoản chưa được gán chi nhánh")

    try:
        return bill_crud.build_bill(db, order_id, voucher_code, only_branch_id)
    except BillError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)

def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload = decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")
    if revoked_crud.is_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=401, detail="Token đã bị thu hồi, vui lòng đăng nhập lại")
    return payload