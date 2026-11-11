from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.menu_item_option import MenuItemOption
    from app.models.order_item import OrderItem


class OrderItemOption(Base):
    __tablename__ = "order_item_options"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"))
    option_id: Mapped[int] = mapped_column(ForeignKey("menu_item_options.id"))
    extra_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))

    order_item: Mapped["OrderItem"] = relationship(back_populates="options")
    option: Mapped["MenuItemOption"] = relationship()

    @property
    def name(self) -> str:
        return self.option.name