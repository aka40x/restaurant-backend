"""CRUD bảng dining_tables (bàn ăn). Router gọi vào đây, không viết SQL trong router."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dining_table import DiningTable
from app.models.order import ORDER_ACTIVE_STATUSES, Order
from app.models.reservation import Reservation
from app.schemas.dining_table import DiningTableCreate, DiningTableUpdate

# Các cột KHÔNG cho phép NULL: FE gửi null thì bỏ qua, tránh lỗi 500 từ MySQL
NOT_NULL_FIELDS = {"table_number", "capacity", "is_active"}

# Đặt bàn đã xếp bàn nhưng khách chưa tới thì còn giữ bàn. Quá giờ đặt ngần này phút thì hệ thống tự
# đánh dấu "không đến" (NO_SHOW_MINUTES bên check-in) nên không còn giữ bàn nữa.
HOLD_AFTER_MINUTES = 30
HOLDING_STATUSES = ("pending", "confirmed")


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


def _holding_reservations(db: Session, table_id: int) -> list[Reservation]:
    """Các đặt bàn đang giữ bàn này: chờ xác nhận / đã xác nhận và chưa quá giờ."""
    deadline = datetime.now() - timedelta(minutes=HOLD_AFTER_MINUTES)
    return list(
        db.scalars(
            select(Reservation)
            .where(
                Reservation.table_id == table_id,
                Reservation.status.in_(HOLDING_STATUSES),
                Reservation.reserved_at >= deadline,
            )
            .order_by(Reservation.reserved_at)
        )
    )


def get_deactivate_blocker(db: Session, table: DiningTable) -> str | None:
    """Lý do CHƯA thể ngừng sử dụng bàn, None nếu ngừng được.

    Căn cứ vào order và đặt bàn thật, không dựa vào cờ `status` của bàn (cờ này có thể lệch).
    """
    has_order = db.scalar(
        select(Order.id).where(Order.table_id == table.id, Order.status.in_(ORDER_ACTIVE_STATUSES)).limit(1)
    )
    if has_order is not None:
        return "Bàn đang có khách (còn order chưa thanh toán), chưa thể ngừng sử dụng"
    reservations = _holding_reservations(db, table.id)
    if reservations:
        r = reservations[0]
        return (
            f"Bàn đã được xếp cho đặt bàn {r.code} lúc {r.reserved_at:%H:%M %d/%m}, "
            "hãy đổi bàn hoặc huỷ đặt bàn đó trước khi ngừng bàn"
        )
    return None


def get_capacity_blocker(db: Session, table: DiningTable, new_capacity: int) -> str | None:
    """Giảm số ghế xuống thấp hơn số khách của đặt bàn đã xếp vào bàn này thì không cho."""
    for r in _holding_reservations(db, table.id):
        if r.party_size > new_capacity:
            return (
                f"Đặt bàn {r.code} đã xếp vào bàn này cho {r.party_size} khách, "
                f"không thể giảm xuống {new_capacity} ghế"
            )
    return None


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