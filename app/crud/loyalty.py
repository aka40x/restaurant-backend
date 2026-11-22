"""Tích điểm theo SĐT khi thanh toán và đổi điểm lấy giảm giá (task T3C6F1E).

Quy tắc:
  - Tích 1 điểm cho mỗi EARN_STEP đồng của tổng thanh toán (làm tròn xuống).
  - Đổi điểm: 1 điểm = POINT_VALUE đồng, tối thiểu MIN_REDEEM điểm mỗi lần. Mỗi lần đổi sinh ra một voucher
    loại 'amount' dùng được 1 lần, nên luồng thanh toán của M5 dùng nguyên ô nhập voucher, không phải sửa.
  - Số dư = tổng điểm trong loyalty_transactions. Mỗi payment chỉ được tích điểm một lần.
Toàn bộ việc ghi nằm trong MỘT transaction, lỗi thì rollback.
"""
import secrets
import string
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.loyalty import LoyaltyTransaction
from app.models.payment import Payment
from app.models.voucher import Voucher

EARN_STEP = 10_000          # đồng cần chi để được 1 điểm
POINT_VALUE = 1_000         # 1 điểm đổi được bấy nhiêu đồng giảm giá
MIN_REDEEM = 10             # số điểm tối thiểu cho một lần đổi
VOUCHER_DAYS = 30           # voucher đổi từ điểm có hạn bấy nhiêu ngày
DEFAULT_NAME = "Khách thân thiết"
_CODE_CHARS = string.ascii_uppercase + string.digits


class LoyaltyError(Exception):
    """Lỗi nghiệp vụ. Router đổi thành HTTPException với status_code và message."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_balance(db: Session, customer_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(LoyaltyTransaction.points), 0)).where(LoyaltyTransaction.customer_id == customer_id)) or 0)


def get_account(db: Session, phone: str, limit: int = 20) -> dict:
    customer = db.scalar(select(Customer).where(Customer.phone == phone))
    if customer is None:
        raise LoyaltyError("Chưa có khách hàng với số điện thoại này", 404)
    history = db.scalars(
        select(LoyaltyTransaction)
        .where(LoyaltyTransaction.customer_id == customer.id)
        .order_by(LoyaltyTransaction.id.desc())
        .limit(limit)
    ).all()
    return {
        "customer_id": customer.id,
        "full_name": customer.full_name,
        "phone": customer.phone,
        "balance": get_balance(db, customer.id),
        "history": history,
    }


def points_for(total_amount: Decimal) -> int:
    return int(Decimal(total_amount) // EARN_STEP)


def earn_points(db: Session, payment_id: int, phone: str, full_name: str | None, only_branch_id: int | None) -> dict:
    """Cộng điểm cho khách (theo SĐT) từ một payment đã thanh toán. Khách chưa có thì tự tạo."""
    try:
        payment = db.get(Payment, payment_id)
        if payment is None:
            raise LoyaltyError("Không tìm thấy thanh toán", 404)
        if payment.status != "paid":
            raise LoyaltyError("Chỉ tích điểm cho thanh toán đã hoàn tất (status = paid)", 409)

        order = db.execute(text("SELECT branch_id FROM orders WHERE id = :id"), {"id": payment.order_id}).mappings().first()
        if only_branch_id is not None and (order is None or order["branch_id"] != only_branch_id):  # BR-02
            raise LoyaltyError("Thanh toán thuộc chi nhánh khác", 403)

        if db.scalar(select(LoyaltyTransaction.id).where(LoyaltyTransaction.payment_id == payment_id)) is not None:
            raise LoyaltyError("Thanh toán này đã được tích điểm rồi", 409)

        earned = points_for(payment.total_amount)
        if earned <= 0:
            raise LoyaltyError(f"Tổng thanh toán chưa đủ {EARN_STEP:,} đ để được 1 điểm".replace(",", "."), 400)

        customer = db.scalar(select(Customer).where(Customer.phone == phone).with_for_update())
        if customer is None:
            customer = Customer(full_name=(full_name or DEFAULT_NAME).strip(), phone=phone)
            db.add(customer)
            db.flush()

        db.add(LoyaltyTransaction(customer_id=customer.id, payment_id=payment_id, type="earn", points=earned))
        db.flush()  # payment_id UNIQUE: hai yêu cầu cùng lúc thì yêu cầu sau bị IntegrityError
        balance = get_balance(db, customer.id)
        db.commit()
        return {"customer_id": customer.id, "payment_id": payment_id, "earned": earned, "balance": balance}
    except IntegrityError:
        db.rollback()
        raise LoyaltyError("Thanh toán này đã được tích điểm rồi", 409)
    except Exception:
        db.rollback()
        raise


def _new_voucher_code(db: Session) -> str:
    for _ in range(10):
        code = "DIEM" + "".join(secrets.choice(_CODE_CHARS) for _ in range(6))
        if db.scalar(select(Voucher.id).where(Voucher.code == code)) is None:
            return code
    raise LoyaltyError("Không tạo được mã voucher, thử lại sau", 500)


def redeem_points(db: Session, phone: str, points: int) -> dict:
    """Trừ điểm của khách và sinh voucher giảm `points x POINT_VALUE` đồng, dùng 1 lần, có hạn."""
    try:
        if points < MIN_REDEEM:
            raise LoyaltyError(f"Mỗi lần đổi tối thiểu {MIN_REDEEM} điểm", 400)
        customer = db.scalar(select(Customer).where(Customer.phone == phone).with_for_update())  # khoá để hai lần đổi cùng lúc không trừ quá số dư
        if customer is None:
            raise LoyaltyError("Chưa có khách hàng với số điện thoại này", 404)
        balance = get_balance(db, customer.id)
        if points > balance:
            raise LoyaltyError(f"Không đủ điểm: khách có {balance} điểm, cần {points} điểm", 409)

        value = Decimal(points * POINT_VALUE)
        today = date.today()
        voucher = Voucher(
            code=_new_voucher_code(db),
            discount_type="amount",
            discount_value=value,
            min_order_amount=value,  # đơn phải từ giá trị voucher trở lên để không "mất oan" điểm
            start_date=today,
            end_date=today + timedelta(days=VOUCHER_DAYS),
            usage_limit=1,
            used_count=0,
            is_active=True,
        )
        db.add(voucher)
        db.flush()
        db.add(LoyaltyTransaction(customer_id=customer.id, voucher_id=voucher.id, type="redeem", points=-points))
        db.commit()
        return {
            "customer_id": customer.id,
            "spent": points,
            "balance": balance - points,
            "voucher_code": voucher.code,
            "discount_value": value,
            "end_date": voucher.end_date,
        }
    except Exception:
        db.rollback()
        raise