"""Truy vấn và quy tắc cho quản lý đặt bàn nội bộ (T3C65C2)."""
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.dining_table import DiningTable
from app.models.reservation import Reservation

HOLD_MINUTES = 120  # thời gian giữ bàn cho một đặt bàn (giống phần đặt bàn của khách)
VALID_STATUSES = {"pending", "confirmed", "seated", "cancelled", "no_show"}
ACTIVE_STATUSES = ("pending", "confirmed", "seated")  # đang chiếm bàn


def to_out(db: Session, r: Reservation) -> dict:
    """Ghép đặt bàn + chi nhánh + bàn thành dict để trả về."""
    branch = db.get(Branch, r.branch_id)
    table = db.get(DiningTable, r.table_id) if r.table_id else None
    return {
        "id": r.id, "code": r.code, "status": r.status, "reserved_at": r.reserved_at,
        "party_size": r.party_size, "guest_name": r.guest_name, "guest_phone": r.guest_phone,
        "note": r.note, "branch": branch, "table": table,
    }


def list_reservations(db: Session, branch_id: int | None, day: date | None, status: str | None) -> list[dict]:
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Trạng thái không hợp lệ")
    stmt = select(Reservation)
    if branch_id is not None:
        stmt = stmt.where(Reservation.branch_id == branch_id)
    if day is not None:
        start = datetime.combine(day, datetime.min.time())
        stmt = stmt.where(Reservation.reserved_at >= start, Reservation.reserved_at < start + timedelta(days=1))
    if status is not None:
        stmt = stmt.where(Reservation.status == status)
    stmt = stmt.order_by(Reservation.reserved_at, Reservation.id)
    return [to_out(db, r) for r in db.scalars(stmt).all()]


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    r = db.get(Reservation, reservation_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đặt bàn")
    return r


def confirm(db: Session, r: Reservation) -> Reservation:
    if r.status != "pending":
        raise HTTPException(status_code=400, detail="Chỉ xác nhận được đặt bàn đang chờ xác nhận")
    r.status = "confirmed"
    db.commit()
    return r


def cancel(db: Session, r: Reservation) -> Reservation:
    if r.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Chỉ huỷ được đặt bàn đang chờ hoặc đã xác nhận")
    r.status = "cancelled"
    db.commit()
    return r


def assign_table(db: Session, r: Reservation, table_id: int) -> Reservation:
    """Xếp bàn / đổi bàn. Kiểm tra: trạng thái, bàn tồn tại, cùng chi nhánh, đủ chỗ, không trùng giờ."""
    if r.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Chỉ xếp hoặc đổi bàn cho đặt bàn đang chờ hoặc đã xác nhận")
    table = db.get(DiningTable, table_id)
    if table is None or not table.is_active:
        raise HTTPException(status_code=404, detail="Không tìm thấy bàn")
    if table.branch_id != r.branch_id:
        raise HTTPException(status_code=400, detail="Bàn không thuộc chi nhánh của đặt bàn này")
    if r.party_size > table.capacity:
        raise HTTPException(status_code=400, detail=f"Bàn chỉ có {table.capacity} chỗ, không đủ cho {r.party_size} khách")

    hold = timedelta(minutes=HOLD_MINUTES)
    others = db.scalars(
        select(Reservation).where(
            Reservation.table_id == table_id,
            Reservation.id != r.id,
            Reservation.status.in_(ACTIVE_STATUSES),
            Reservation.reserved_at > r.reserved_at - hold,
            Reservation.reserved_at < r.reserved_at + hold,
        )
    ).first()
    if others is not None:
        raise HTTPException(status_code=409, detail=f"Bàn đã có đặt bàn {others.code} gần giờ này")

    r.table_id = table_id
    db.commit()
    return r