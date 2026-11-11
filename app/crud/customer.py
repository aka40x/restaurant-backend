"""CRUD = các hàm đọc/ghi DB cho bảng customers."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_customer_by_phone(db: Session, phone: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.phone == phone))