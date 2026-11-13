"""Schema hoá đơn tạm (M5): kết quả tính tiền một order, có áp voucher nếu gửi mã."""
from decimal import Decimal

from pydantic import BaseModel


class BillLineOut(BaseModel):
    """Một dòng món trong hoá đơn (đã bỏ món bị huỷ)."""

    order_item_id: int
    menu_item_id: int
    name: str
    quantity: int
    unit_price: Decimal  # giá lưu lúc gọi món
    options_price: Decimal  # tổng extra_price của size/topping cho một phần
    line_total: Decimal  # (unit_price + options_price) x quantity


class BillOut(BaseModel):
    """Dữ liệu API trả về cho FE khi xem hoá đơn tạm."""

    order_id: int
    branch_id: int
    lines: list[BillLineOut]
    subtotal: Decimal  # tạm tính
    voucher_code: str | None  # None nếu không áp voucher
    discount_amount: Decimal  # số tiền giảm
    total_amount: Decimal  # tổng phải trả
