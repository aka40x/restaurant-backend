"""API check-in và đánh dấu không đến (T3C65F6).

    PUT /api/reservations/{id}/check-in   khách đến: seated + bàn occupied + mở order
    PUT /api/reservations/{id}/no-show    đánh dấu khách không đến

Chỉ nhân viên (admin, manager, waiter), trong chi nhánh của mình. Include SAU router đặt bàn của khách.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, WAITER, check_branch_access, require_roles
from app.crud import reservation_admin as admin_crud
from app.crud import reservation_checkin as crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.reservation_admin import ReservationAdminOut
from app.schemas.reservation_checkin import CheckInOut

router = APIRouter(prefix="/reservations", tags=["Đặt bàn - check-in"])

staff = require_roles(MANAGER, WAITER)  # admin luôn được phép


def _load(db: Session, reservation_id: int, user: User):
    r = admin_crud.get_reservation(db, reservation_id)
    check_branch_access(user, r.branch_id)
    return r


@router.put("/{reservation_id}/check-in", response_model=CheckInOut, summary="Check-in: khách đến, mở order cho bàn")
def check_in(reservation_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    r, order_id = crud.check_in(db, user, _load(db, reservation_id, user))
    return {**admin_crud.to_out(db, r), "order_id": order_id}


@router.put("/{reservation_id}/no-show", response_model=ReservationAdminOut, summary="Đánh dấu khách không đến")
def no_show(reservation_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return admin_crud.to_out(db, crud.mark_no_show(db, _load(db, reservation_id, user)))