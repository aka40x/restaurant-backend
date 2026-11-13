"""Model đặt bàn (bảng `reservations`).

status: pending / confirmed / seated / cancelled / no_show
table_id trống đến khi nhân viên xếp bàn; customer_id trống nếu là khách vãng lai.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.branch import Branch
from app.models.customer import Customer
from app.models.dining_table import DiningTable
 

class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (Index("idx_reservations_branch_time", "branch_id", "reserved_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)  # mã để khách tra cứu / huỷ
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    table_id: Mapped[int | None] = mapped_column(ForeignKey("dining_tables.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    guest_name: Mapped[str] = mapped_column(String(100))
    guest_phone: Mapped[str] = mapped_column(String(20))
    party_size: Mapped[int]  # số người
    reserved_at: Mapped[datetime] = mapped_column(DateTime)  # giờ khách đến
    status: Mapped[str] = mapped_column(String(20), default="pending")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    branch: Mapped[Branch] = relationship()
    table: Mapped[DiningTable | None] = relationship()
    customer: Mapped[Customer | None] = relationship()