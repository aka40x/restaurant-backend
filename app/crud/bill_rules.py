"""Quy tắc tính tiền và kiểm tra voucher (M5). File này không đọc DB nên dễ kiểm tra riêng.

Căn cứ: BR-08 (dùng giá đã lưu), BR-11 (điều kiện voucher), BR-12 (cách giảm giá).
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


class BillError(Exception):
    """Lỗi nghiệp vụ khi tính tiền. Router đổi thành HTTPException với status_code và message."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def money(value) -> Decimal:
    """Làm tròn về 2 chữ số thập phân, giống DECIMAL(10,2) trong DB."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def line_total(unit_price: Decimal, options_price: Decimal, quantity: int) -> Decimal:
    """Thành tiền một dòng = (đơn giá + giá tuỳ chọn) x số lượng."""
    return money((Decimal(unit_price) + Decimal(options_price)) * quantity)


def _vnd(value: Decimal) -> str:
    return f"{value:,.0f}".replace(",", ".") + " đ"


def check_voucher(voucher, subtotal: Decimal, today: date) -> None:
    """Kiểm tra voucher có áp dụng được cho đơn tạm tính `subtotal` vào ngày `today` không.

    Hợp lệ thì không làm gì, không hợp lệ thì ném BillError nêu rõ lý do.
    """
    if not voucher.is_active:
        raise BillError("Voucher đã ngừng hoạt động")
    if today < voucher.start_date:
        raise BillError("Voucher chưa đến ngày áp dụng")
    if today > voucher.end_date:
        raise BillError("Voucher đã hết hạn")
    if subtotal < voucher.min_order_amount:
        raise BillError(f"Đơn hàng chưa đạt giá trị tối thiểu {_vnd(Decimal(voucher.min_order_amount))} để dùng voucher")
    if voucher.usage_limit is not None and voucher.used_count >= voucher.usage_limit:
        raise BillError("Voucher đã hết lượt sử dụng")


def calc_discount(voucher, subtotal: Decimal) -> Decimal:
    """Số tiền giảm: percent = tạm tính x giá trị / 100, amount = giá trị. Không vượt quá tạm tính."""
    if voucher.discount_type == "percent":
        discount = Decimal(subtotal) * Decimal(voucher.discount_value) / Decimal(100)
    else:
        discount = Decimal(voucher.discount_value)
    return min(money(discount), money(subtotal))


def make_totals(subtotal: Decimal, voucher, today: date) -> tuple[Decimal, Decimal]:
    """Trả (giảm giá, tổng tiền). Không có voucher thì giảm giá bằng 0. Tổng tiền không âm."""
    subtotal = money(subtotal)
    if voucher is None:
        return Decimal("0.00"), subtotal
    check_voucher(voucher, subtotal, today)
    discount = calc_discount(voucher, subtotal)
    return discount, max(subtotal - discount, Decimal("0.00"))
