"""Đọc dữ liệu order và dựng hoá đơn tạm (M5).

Module Order (M4) do người khác làm, nên ở đây chỉ ĐỌC các bảng orders, order_items,
order_item_options bằng câu SQL, không import model của M4 và không sửa dữ liệu của họ.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.crud.bill_rules import BillError, line_total, make_totals, money
from app.models.voucher import Voucher
from app.schemas.bill import BillLineOut, BillOut

# Dòng món chưa bị huỷ, kèm tổng giá tuỳ chọn. Giá lấy từ order_items / order_item_options (giá lúc gọi món),
# bảng menu_items chỉ dùng để lấy tên hiển thị.
_LINES_SQL = text(
    """
    SELECT oi.id AS order_item_id, oi.menu_item_id, mi.name, oi.quantity, oi.unit_price,
           COALESCE(SUM(oio.extra_price), 0) AS options_price
    FROM order_items oi
    JOIN menu_items mi ON mi.id = oi.menu_item_id
    LEFT JOIN order_item_options oio ON oio.order_item_id = oi.id
    WHERE oi.order_id = :order_id AND oi.status <> 'cancelled'
    GROUP BY oi.id, oi.menu_item_id, mi.name, oi.quantity, oi.unit_price
    ORDER BY oi.id
    """
)


def get_voucher_by_code(db: Session, code: str) -> Voucher | None:
    return db.scalar(select(Voucher).where(Voucher.code == code))


def build_bill(
    db: Session,
    order_id: int,
    voucher_code: str | None = None,
    only_branch_id: int | None = None,
    today: date | None = None,
) -> BillOut:
    """Tính tiền order: tạm tính, giảm giá (nếu có voucher), tổng. Lỗi nghiệp vụ thì ném BillError.

    only_branch_id: nếu có, chỉ cho tính order của chi nhánh này (BR-02). admin truyền None để xem mọi chi nhánh.
    """
    today = today or date.today()

    order = db.execute(
        text("SELECT id, branch_id, status FROM orders WHERE id = :id"), {"id": order_id}
    ).mappings().first()
    if order is None:
        raise BillError("Không tìm thấy order", 404)
    if only_branch_id is not None and order["branch_id"] != only_branch_id:  # BR-02
        raise BillError("Order thuộc chi nhánh khác", 403)
    if order["status"] == "paid":  # BR-09
        raise BillError("Order đã thanh toán, không thể tính lại", 409)
    if order["status"] == "cancelled":
        raise BillError("Order đã bị huỷ, không thể tính tiền", 409)

    lines: list[BillLineOut] = []
    for row in db.execute(_LINES_SQL, {"order_id": order_id}).mappings():
        options_price = Decimal(row["options_price"])
        lines.append(
            BillLineOut(
                order_item_id=row["order_item_id"],
                menu_item_id=row["menu_item_id"],
                name=row["name"],
                quantity=row["quantity"],
                unit_price=money(row["unit_price"]),
                options_price=money(options_price),
                line_total=line_total(row["unit_price"], options_price, row["quantity"]),
            )
        )
    subtotal = money(sum((line.line_total for line in lines), Decimal("0")))

    voucher = None
    code = (voucher_code or "").strip().upper() or None
    if code:
        voucher = get_voucher_by_code(db, code)
        if voucher is None:
            raise BillError("Mã voucher không tồn tại", 404)

    discount, total = make_totals(subtotal, voucher, today)
    return BillOut(
        order_id=order["id"],
        branch_id=order["branch_id"],
        lines=lines,
        subtotal=subtotal,
        voucher_code=code,
        discount_amount=discount,
        total_amount=total,
    )
