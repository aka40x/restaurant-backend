"""CRUD bảng dining_tables (bàn ăn). Router gọi vào đây, không viết SQL trong router."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dining_table import DiningTable
from app.schemas.dining_table import DiningTableCreate, DiningTableUpdate

# Các cột KHÔNG cho phép NULL: FE gửi null thì bỏ qua, tránh lỗi 500 từ MySQL
NOT_NULL_FIELDS = {"table_number", "capacity", "status", "is_active"}


class DuplicateTableNumber(Exception):
    """Số bàn đã có trong chi nhánh (BR-03). Router đổi thành lỗi 409."""


def get_tables(
    db: Session,
    branch_id: int | None = None,
    keyword: str | None = None,
    area: str | None = None,
    only_active: bool = False,
) -> list[DiningTable]:
    query = select(DiningTable).order_by(DiningTable.branch_id, DiningTable.area, DiningTable.table_number)
    if branch_id is not None:
        query = query.where(DiningTable.branch_id == branch_id)
    if keyword:
        query = query.where(DiningTable.table_number.contains(keyword))
    if area:
        query = query.where(DiningTable.area == area)
    if only_active:
        query = query.where(DiningTable.is_active.is_(True))
    return list(db.scalars(query))


def get_table(db: Session, table_id: int) -> DiningTable | None:
    return db.get(DiningTable, table_id)


def get_table_by_number(db: Session, branch_id: int, table_number: str) -> DiningTable | None:
    # So sánh không phân biệt hoa/thường cho giống cách MySQL kiểm tra UNIQUE ("a01" = "A01")
    return db.scalar(
        select(DiningTable).where(
            DiningTable.branch_id == branch_id,
            func.lower(DiningTable.table_number) == table_number.lower(),
        )
    )


def _clean_area(area: str | None) -> str | None:
    return area or None  # chuỗi rỗng -> NULL


def create_table(db: Session, data: DiningTableCreate) -> DiningTable:
    if get_table_by_number(db, data.branch_id, data.table_number):
        raise DuplicateTableNumber
    values = data.model_dump()
    values["area"] = _clean_area(values["area"])
    table = DiningTable(**values)
    db.add(table)
    try:
        db.commit()
    except IntegrityError:  # hai người thêm cùng lúc: UNIQUE của MySQL chặn
        db.rollback()
        raise DuplicateTableNumber
    db.refresh(table)
    return table


def update_table(db: Session, table: DiningTable, data: DiningTableUpdate) -> DiningTable:
    changes = data.model_dump(exclude_unset=True)
    new_number = changes.get("table_number")
    if new_number is not None and new_number.lower() != table.table_number.lower():
        if get_table_by_number(db, table.branch_id, new_number):
            raise DuplicateTableNumber
    for field, value in changes.items():
        if value is None and field in NOT_NULL_FIELDS:
            continue
        setattr(table, field, _clean_area(value) if field == "area" else value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateTableNumber
    db.refresh(table)
    return table


def deactivate_table(db: Session, table: DiningTable) -> None:
    # Không xoá thật: order và đặt bàn cũ vẫn trỏ tới bàn này. Chỉ đánh dấu ngừng sử dụng.
    table.is_active = False
    db.commit()