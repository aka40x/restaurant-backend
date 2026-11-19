"""Thanh toán và đóng order (M5), căn cứ FR-PAY-03, BR-09, BR-10, BR-11, BR-12, NFR-07.

Toàn bộ việc ghi nằm trong MỘT transaction: lỗi ở bước nào thì db.rollback(), không để dữ liệu dở dang.
Module Order (M4) và Bàn (M2) do người khác làm, nên ở đây chỉ UPDATE vài cột theo đúng đặc tả
(orders.status, orders.closed_at, dining_tables.status) bằng câu SQL, không import model của họ.
"""
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.bill import build_bill
from app.crud.bill_rules import BillError, make_totals
from app.models.payment import Payment
from app.models.voucher import Voucher
from app.schemas.payment import PaymentCreate

# Trạng thái order cho phép thanh toán (init.sql: open / sent / served / paid / cancelled).
# Cần chốt lại với người làm module Order nếu nhóm muốn chỉ cho thanh toán khi đã 'served'.
PAYABLE_STATUSES = {"open", "sent", "served"}


def pay_order(db: Session, data: PaymentCreate, cashier_id: int, only_branch_id: int | None = None) -> Payment:
    """Thanh toán một order: tính lại tiền, kiểm tra lại voucher, ghi payments, đóng order, trả bàn.

    only_branch_id: chỉ cho thanh toán order của chi nhánh này (BR-02). admin truyền None.
    Lỗi nghiệp vụ thì ném BillError (router đổi thành HTTPException).
    """
    try:
        # Khoá dòng order: hai thu ngân bấm thanh toán cùng lúc thì người đến sau phải chờ
        order = db.execute(
            text("SELECT id, branch_id, table_id, status FROM orders WHERE id = :id FOR UPDATE"),
            {"id": data.order_id},
        ).mappings().first()
        if order is None:
            raise BillError("Không tìm thấy order", 404)
        if only_branch_id is not None and order["branch_id"] != only_branch_id:  # BR-02
            raise BillError("Order thuộc chi nhánh khác", 403)
        if order["status"] == "paid":
            raise BillError("Order đã được thanh toán", 409)
        if order["status"] == "cancelled":
            raise BillError("Order đã bị huỷ, không thể thanh toán", 409)
        if order["status"] not in PAYABLE_STATUSES:
            raise BillError(f"Order đang ở trạng thái '{order['status']}', chưa thể thanh toán", 409)

        already_paid = db.execute(
            text("SELECT id FROM payments WHERE order_id = :id"), {"id": data.order_id}
        ).first()
        if already_paid is not None:  # BR-10: mỗi order tối đa một thanh toán
            raise BillError("Order đã có thanh toán", 409)

        # Tính lại tiền ngay lúc thanh toán (không tin số tiền FE đã xem trước đó)
        bill = build_bill(db, data.order_id, data.voucher_code, only_branch_id)
        if not bill.lines:
            raise BillError("Order chưa có món nào để thanh toán", 400)

        # Khoá dòng voucher rồi kiểm tra lại: lượt dùng có thể vừa bị người khác dùng hết
        voucher = None
        if bill.voucher_code:
            voucher = db.scalar(
                select(Voucher)
                .where(Voucher.code == bill.voucher_code)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if voucher is None:
                raise BillError("Mã voucher không tồn tại", 404)
        discount, total = make_totals(bill.subtotal, voucher, date.today())

        payment = Payment(
            order_id=data.order_id,
            cashier_id=cashier_id,
            voucher_id=voucher.id if voucher else None,
            subtotal=bill.subtotal,
            discount_amount=discount,
            total_amount=total,
            method=data.method,
            status="paid",
        )
        db.add(payment)
        db.flush()  # lỗi ràng buộc (vd order_id trùng) hiện ra ngay ở đây

        db.execute(
            text("UPDATE orders SET status = 'paid', closed_at = NOW() WHERE id = :id"),
            {"id": data.order_id},
        )
        # Trả bàn về trống, trừ khi bàn đó còn order khác chưa thanh toán
        db.execute(
            text(
                """
                UPDATE dining_tables SET status = 'available'
                WHERE id = :table_id
                  AND NOT EXISTS (
                      SELECT 1 FROM orders o
                      WHERE o.table_id = :table_id AND o.id <> :order_id
                        AND o.status NOT IN ('paid', 'cancelled')
                  )
                """
            ),
            {"table_id": order["table_id"], "order_id": data.order_id},
        )
        if voucher is not None:
            voucher.used_count += 1

        db.commit()
        db.refresh(payment)
        return payment
    except IntegrityError:
        db.rollback()
        raise BillError("Order đã có thanh toán", 409)
    except Exception:
        db.rollback()
        raise
