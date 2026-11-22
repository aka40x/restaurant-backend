"""API khách hàng thân thiết (task T3C6F1E). Đường dẫn đầy đủ: /api/loyalty

    GET  /api/loyalty/{phone}    xem số dư và lịch sử điểm của khách (theo SĐT)
    POST /api/loyalty/earn       tích điểm cho một thanh toán đã hoàn tất: { payment_id, phone, full_name? }
    POST /api/loyalty/redeem     đổi điểm lấy voucher giảm giá dùng 1 lần: { phone, points }

Quyền: cashier (đúng chi nhánh của thanh toán), manager và admin.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.core.deps import CASHIER, MANAGER, get_branch_scope, require_roles
from app.crud import loyalty as loyalty_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.loyalty import PHONE_PATTERN, EarnOut, EarnRequest, LoyaltyAccountOut, RedeemOut, RedeemRequest

router = APIRouter(prefix="/loyalty", tags=["Khách thân thiết"])

LOYALTY_ROLES = (CASHIER, MANAGER)


def _raise(error: loyalty_crud.LoyaltyError):
    raise HTTPException(status_code=error.status_code, detail=error.message)


@router.get("/{phone}", response_model=LoyaltyAccountOut)
def get_loyalty_account(
    phone: str = Path(description="Số điện thoại khách, VD 0912345678"),
    user: User = Depends(require_roles(*LOYALTY_ROLES)),
    db: Session = Depends(get_db),
):
    if not re.match(PHONE_PATTERN, phone):
        raise HTTPException(status_code=422, detail="Số điện thoại không hợp lệ")
    try:
        return loyalty_crud.get_account(db, phone)
    except loyalty_crud.LoyaltyError as error:
        _raise(error)


@router.post("/earn", response_model=EarnOut, status_code=201)
def earn_points(
    data: EarnRequest,
    user: User = Depends(require_roles(*LOYALTY_ROLES)),
    db: Session = Depends(get_db),
):
    try:
        return loyalty_crud.earn_points(db, data.payment_id, data.phone, data.full_name, get_branch_scope(user))
    except loyalty_crud.LoyaltyError as error:
        _raise(error)


@router.post("/redeem", response_model=RedeemOut, status_code=201)
def redeem_points(
    data: RedeemRequest,
    user: User = Depends(require_roles(*LOYALTY_ROLES)),
    db: Session = Depends(get_db),
):
    try:
        return loyalty_crud.redeem_points(db, data.phone, data.points)
    except loyalty_crud.LoyaltyError as error:
        _raise(error)