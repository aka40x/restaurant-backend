"""Model khách hàng (bảng `customers`). Khách tra theo số điện thoại (duy nhất); password_hash trống nếu khách không đăng ký tài khoản."""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # trống nếu không đăng ký
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now()) 