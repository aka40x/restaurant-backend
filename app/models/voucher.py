"""Model voucher (bảng `vouchers`): mã giảm giá, điều kiện áp dụng, hạn dùng, lượt dùng (M5).

Cột phải khớp với câu CREATE TABLE trong sql/init.sql.
"""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.payment import Payment


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    discount_type: Mapped[str] = mapped_column(String(10))  # 'percent' hoặc 'amount'
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # % hoặc số tiền giảm
    min_order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # trống = không giới hạn lượt
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # False = ngừng dùng (xoá mềm)

    payments: Mapped[list["Payment"]] = relationship(back_populates="voucher")