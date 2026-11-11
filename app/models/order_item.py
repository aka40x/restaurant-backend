from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.order_item_option import OrderItemOption

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
if TYPE_CHECKING:
    from app.models.menu_item import MenuItem
    from app.models.order import Order

# Trạng thái món: chờ -> đang nấu -> xong -> đã ra món; hoặc huỷ
ITEM_PENDING = "pending"
ITEM_COOKING = "cooking"
ITEM_DONE = "done"
ITEM_SERVED = "served"
ITEM_CANCELLED = "cancelled"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default=ITEM_PENDING)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
        # Thời điểm gửi bếp. NULL = chưa gửi (waiter còn sửa / huỷ được).
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    order: Mapped["Order"] = relationship(back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship()
    options: Mapped[list[OrderItemOption]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan", order_by="OrderItemOption.id"
    )

    @property
    def menu_item_name(self) -> str:
        return self.menu_item.name

    @property
    def line_total(self) -> Decimal:
        """(giá món + giá các tuỳ chọn) x số lượng."""
        extra = sum((o.extra_price for o in self.options), Decimal("0"))
        return (self.unit_price + extra) * self.quantity