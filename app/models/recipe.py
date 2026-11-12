"""Model công thức (bảng `recipes`): một món dùng nguyên liệu nào, bao nhiêu cho một phần (M5).

Cột phải khớp với câu CREATE TABLE trong sql/init.sql.
"""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("menu_item_id", "ingredient_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))  # menu_items là bảng của M2
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    quantity_needed: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # lượng nguyên liệu cho một phần món

    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipes")