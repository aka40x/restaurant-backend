"""Model nguyên liệu (bảng `ingredients`) (M5).

Cột phải khớp với câu CREATE TABLE trong sql/init.sql.
"""
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.branch_inventory import BranchInventory
    from app.models.recipe import Recipe


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20))  # g, ml, cái...

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="ingredient")
    inventories: Mapped[list["BranchInventory"]] = relationship(back_populates="ingredient")