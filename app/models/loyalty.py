"""Model giao dịch điểm thân thiết (bảng `loyalty_transactions`).

Số dư điểm của khách = tổng cột `points` của khách đó (điểm cộng là số dương, điểm đổi là số âm),
nên không cần thêm cột vào bảng customers. Mỗi payment chỉ được tích điểm một lần (payment_id UNIQUE).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), unique=True, nullable=True)  # chỉ có ở giao dịch 'earn'
    voucher_id: Mapped[int | None] = mapped_column(ForeignKey("vouchers.id"), nullable=True)  # chỉ có ở giao dịch 'redeem'
    type: Mapped[str] = mapped_column(String(10))  # 'earn' (tích điểm) hoặc 'redeem' (đổi điểm)
    points: Mapped[int] = mapped_column(Integer)  # earn: số dương, redeem: số âm
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())