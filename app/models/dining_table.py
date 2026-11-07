"""Model bàn ăn (bảng `dining_tables`). Số bàn không trùng trong cùng chi nhánh (BR-03)."""
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.branch import Branch


class DiningTable(Base):
    __tablename__ = "dining_tables"
    __table_args__ = (UniqueConstraint("branch_id", "table_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    table_number: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int]  # số ghế
    area: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Tầng 1, Sân vườn...
    status: Mapped[str] = mapped_column(String(20), default="available")  # available / occupied / reserved
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    branch: Mapped[Branch] = relationship()