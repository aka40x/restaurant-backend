"""Check-in khách và đánh dấu không đến (T3C65F6).

- Check-in: đặt bàn confirmed + đã xếp bàn -> seated, mở order cho bàn (dùng hàm của module Order,
  hàm đó cũng chuyển bàn sang occupied và chặn khi bàn đang có order chưa thanh toán).
- Không đến: nhân viên đánh dấu tay, hoặc hệ thống tự đánh dấu khi quá giờ NO_SHOW_MINUTES phút.
"""
from datetime import datetime, timedelta
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.crud import user as _user_crud  # noqa: F401 - import trước để tránh vòng import deps <-> user
from app.crud import order as order_crud
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.order import OrderCreate


NO_SHOW_MINUTES = 30  # quá giờ đặt bao nhiêu phút thì tự đánh dấu không đến
OVERDUE_STATUSES = ("pending", "confirmed")  # đặt bàn chưa nhận bàn


def mark_overdue_no_shows(db: Session, now: datetime | None = None) -> int:
    """Chuyển mọi đặt bàn pending/confirmed đã quá giờ hơn NO_SHOW_MINUTES phút sang no_show. Trả về số dòng đổi."""
    deadline = (now or datetime.now()) - timedelta(minutes=NO_SHOW_MINUTES)
    result = db.execute(
        update(Reservation)
        .where(Reservation.status.in_(OVERDUE_STATUSES), Reservation.reserved_at < deadline)
        .values(status="no_show")
    )
    db.commit()
    return result.rowcount


def check_in(db: Session, user: User, r: Reservation) -> tuple[Reservation, int]:
    """Check-in khách đến. Trả về (đặt bàn, id order vừa mở)."""
    mark_overdue_no_shows(db)  # đơn đã quá giờ thì không check-in được nữa
    db.refresh(r)
    if r.status == "seated":
        raise HTTPException(status_code=409, detail="Đặt bàn này đã check-in rồi")
    if r.status == "no_show":
        raise HTTPException(status_code=400, detail=f"Đặt bàn đã quá giờ hơn {NO_SHOW_MINUTES} phút, bị đánh dấu không đến")
    if r.status == "pending":
        raise HTTPException(status_code=400, detail="Đặt bàn chưa được xác nhận, hãy xác nhận trước khi check-in")
    if r.status != "confirmed":
        raise HTTPException(status_code=400, detail="Chỉ check-in được đặt bàn đã xác nhận")
    if r.table_id is None:
        raise HTTPException(status_code=400, detail="Đặt bàn chưa được xếp bàn, hãy xếp bàn trước khi check-in")

    # Mở order cho bàn (kiểm tra quyền chi nhánh, bàn đang bận -> 409, bàn -> occupied nằm trong hàm này)
    order = order_crud.open_order(
        db, user, OrderCreate(table_id=r.table_id, reservation_id=r.id, note=f"Khách đặt bàn {r.code}")
    )
    r.status = "seated"
    db.commit()
    return r, order.id


def mark_no_show(db: Session, r: Reservation) -> Reservation:
    """Nhân viên đánh dấu khách không đến. Chỉ được khi đã tới giờ đặt."""
    if r.status not in OVERDUE_STATUSES:
        raise HTTPException(status_code=400, detail="Chỉ đánh dấu không đến cho đặt bàn đang chờ hoặc đã xác nhận")
    if r.reserved_at > datetime.now():
        raise HTTPException(status_code=400, detail="Chưa tới giờ đặt bàn, chưa thể đánh dấu không đến")
    r.status = "no_show"
    db.commit()
    return r