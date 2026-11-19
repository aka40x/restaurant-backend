"""Model tồn kho theo chi nhánh (bảng `branch_inventories`) (M5).

Cột phải khớp với câu CREATE TABLE trong sql/init.sql.
"""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient


class BranchInventory(Base):
    __tablename__ = "branch_inventories"
    __table_args__ = (
        UniqueConstraint("branch_id", "ingredient_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # tồn hiện tại
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # dưới mức này thì cảnh báo

    ingredient: Mapped["Ingredient"] = relationship(back_populates="inventories")