"""CRUD = các hàm đọc/ghi DB cho bảng users."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))