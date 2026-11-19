"""API thanh toán (M5). Đường dẫn đầy đủ: /api/payments

    GET /api/payments/bill/{order_id}   xem hoá đơn tạm của order (tạm tính, giảm giá, tổng).
                                        Gửi thêm ?voucher_code=WELCOME10 để áp voucher.
    POST /api/payments                  thanh toán order: ghi payments, đóng order, trả bàn (một transaction)

Quyền xem hoá đơn: cashier, manager (đúng chi nhánh của order) và admin (mọi chi nhánh).
Thanh toán (POST): chỉ cashier, đúng chi nhánh của order.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import bill as bill_crud
from app.crud import payment as payment_crud
from app.crud.bill_rules import BillError
from app.db.session import get_db
from app.models.user import User
from app.schemas.bill import BillOut
from app.schemas.payment import PaymentCreate, PaymentOut

router = APIRouter(prefix="/payments", tags=["Payments"])

BILL_ROLES = {"admin", "manager", "cashier"}
PAY_ROLES = {"cashier"}


def get_token_payload(user: User = Depends(get_current_user)) -> dict:
    """Lấy người dùng từ token qua get_current_user dùng chung của cả hệ thống.

    get_current_user đã kiểm tra: token hợp lệ, chưa bị thu hồi (logout), tài khoản còn tồn tại
    và còn hoạt động. Vai trò và chi nhánh lấy từ DB nên đổi vai trò hay khoá tài khoản có hiệu lực ngay.
    """
    return {"sub": user.id, "role": user.role.name, "branch_id": user.branch_id}


@router.get("/bill/{order_id}", response_model=BillOut)
def get_bill(
    order_id: int,
    voucher_code: str | None = None,
    claims: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
):
    role = claims.get("role")

    if role not in BILL_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Chỉ thu ngân, quản lý hoặc admin mới xem được hoá đơn"
        )

    # Admin xem mọi chi nhánh.
    # Cashier và manager chỉ xem order thuộc chi nhánh mình.
    only_branch_id = None

    if role != "admin":
        only_branch_id = claims.get("branch_id")

        if only_branch_id is None:
            raise HTTPException(
                status_code=403,
                detail="Tài khoản chưa được gán chi nhánh"
            )

    try:
        return bill_crud.build_bill(
            db,
            order_id,
            voucher_code,
            only_branch_id
        )
    except BillError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )


@router.post("", response_model=PaymentOut, status_code=201)
def create_payment(
    data: PaymentCreate,
    claims: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
):
    if claims.get("role") not in PAY_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Chỉ thu ngân mới được thanh toán order"
        )

    # Thu ngân chỉ thanh toán order thuộc chi nhánh mình.
    branch_id = claims.get("branch_id")

    if branch_id is None:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản chưa được gán chi nhánh"
        )

    try:
        # cashier_id lấy từ tài khoản đang đăng nhập, không nhận từ FE.
        return payment_crud.pay_order(
            db,
            data,
            int(claims["sub"]),
            branch_id
        )
    except BillError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )