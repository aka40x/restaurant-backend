"""Model tuỳ chọn của món (bảng `menu_item_options`): size, topping và giá cộng thêm."""
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.menu_item import MenuItem


class MenuItemOption(Base):
    __tablename__ = "menu_item_options"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    name: Mapped[str] = mapped_column(String(100))  # vd: Size L, Thêm phô mai
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)  # S, M, L (trống nếu là topping)
    topping: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Phô mai (trống nếu là size)
    extra_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)  # giá cộng thêm
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)  # bắt buộc chọn?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    menu_item: Mapped[MenuItem] = relationship(back_populates="options")