"""Model thanh toán (bảng `payments`): mỗi order có tối đa một dòng thanh toán (M5).

Cột phải khớp với câu CREATE TABLE trong sql/init.sql.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.voucher import Voucher


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # TODO: khi model Order (M4) được merge vào main, đổi thành
    #       mapped_column(ForeignKey("orders.id"), unique=True). Khoá ngoại trong DB vẫn có sẵn nhờ init.sql.
    order_id: Mapped[int] = mapped_column(Integer, unique=True)
    cashier_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    voucher_id: Mapped[int | None] = mapped_column(ForeignKey("vouchers.id"), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # tạm tính
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # tổng phải trả
    method: Mapped[str] = mapped_column(String(20))  # 'cash', 'card' hoặc 'transfer'
    status: Mapped[str] = mapped_column(String(20), default="paid")  # 'paid' hoặc 'refunded'
    paid_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    voucher: Mapped[Voucher | None] = relationship(back_populates="payments")