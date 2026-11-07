"""Model danh mục món (bảng `categories`). Không xoá cứng, chỉ đặt is_active = False (BR-14)."""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0)  # thứ tự hiển thị
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)