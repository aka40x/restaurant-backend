"""Quy tắc trừ kho (M5), căn cứ FR-INV-02, FR-INV-03 và BR-13. File này không đọc DB nên dễ kiểm tra riêng."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")  # số lượng nguyên liệu trong kho lưu DECIMAL(10,2)


def _round(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def amount_needed(quantity_needed: Decimal, dish_quantity: int) -> Decimal:
    """Lượng nguyên liệu cần cho `dish_quantity` phần món = lượng một phần x số phần."""
    return _round(Decimal(quantity_needed) * Decimal(dish_quantity))


def apply_consumption(current: Decimal, minimum: Decimal, needed: Decimal) -> tuple[Decimal, bool]:
    """Trừ `needed` khỏi tồn `current`. Trả về (tồn mới, vừa rơi xuống dưới mức tối thiểu).

    - Tồn không xuống dưới 0: bếp đã nấu xong rồi nên không chặn, chỉ ghi nhận là hết hàng.
    - "Vừa rơi" nghĩa là trước khi trừ chưa dưới mức tối thiểu, sau khi trừ thì dưới (BR-13).
    """
    current, minimum, needed = _round(current), _round(minimum), _round(needed)
    new_quantity = max(current - needed, Decimal("0.00"))
    just_became_low = current >= minimum and new_quantity < minimum
    return new_quantity, just_became_low
