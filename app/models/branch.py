"""Model chi nhánh (bảng `branches`). Đây là model mẫu, các module khác copy file này để làm bảng của mình.

Cột phải khớp với câu CREATE TABLE trong sql/init.sql.
"""
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    open_time: Mapped[time] = mapped_column(Time, default=time(10, 0))
    close_time: Mapped[time] = mapped_column(Time, default=time(22, 0))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
