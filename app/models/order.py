from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.order_item import ITEM_CANCELLED, OrderItem

ORDER_OPEN = "open"
ORDER_SENT = "sent"
ORDER_SERVED = "served"
ORDER_PAID = "paid"
ORDER_CANCELLED = "cancelled"
# Order còn đang phục vụ (chưa thanh toán, chưa huỷ): còn sửa món được, và 1 bàn chỉ có 1 order như vậy
ORDER_ACTIVE_STATUSES = (ORDER_OPEN, ORDER_SENT, ORDER_SERVED)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    table_id: Mapped[int] = mapped_column(ForeignKey("dining_tables.id"))
    # FK tới reservations.id đã có trong sql/init.sql. Khi M3 viết xong model Reservation thì đổi thành
    # mapped_column(ForeignKey("reservations.id"), nullable=True) cho đồng bộ.
    reservation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    waiter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default=ORDER_OPEN)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )

    @property
    def subtotal(self) -> Decimal:
        """Tạm tính = tổng thành tiền các món, KHÔNG tính món đã huỷ."""
        return sum((i.line_total for i in self.items if i.status != ITEM_CANCELLED), Decimal("0"))