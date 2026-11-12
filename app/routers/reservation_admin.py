"""API quản lý đặt bàn nội bộ (T3C65C2): xem danh sách, xác nhận, xếp / đổi bàn, huỷ.

Chỉ nhân viên (admin, manager, waiter). Nhân viên chỉ thấy đặt bàn của chi nhánh mình.
Router này phải include SAU router đặt bàn của khách để /lookup không bị nhận nhầm là {id}.
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, WAITER, check_branch_access, require_roles, resolve_branch_id
from app.crud import reservation_admin as crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.reservation_admin import AssignTable, ReservationAdminOut

router = APIRouter(prefix="/reservations", tags=["Đặt bàn - nội bộ"])

staff = require_roles(MANAGER, WAITER)  # admin luôn được phép


def _load(db: Session, reservation_id: int, user: User):
    r = crud.get_reservation(db, reservation_id)
    check_branch_access(user, r.branch_id)
    return r


@router.get("", response_model=list[ReservationAdminOut], summary="Danh sách đặt bàn (lọc theo chi nhánh, ngày, trạng thái)")
def list_reservations(
    branch_id: int | None = None,
    date: date | None = None,
    status: str | None = None,
    user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    return crud.list_reservations(db, resolve_branch_id(user, branch_id), date, status)


@router.get("/{reservation_id}", response_model=ReservationAdminOut, summary="Chi tiết một đặt bàn")
def get_reservation(reservation_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return crud.to_out(db, _load(db, reservation_id, user))


@router.put("/{reservation_id}/confirm", response_model=ReservationAdminOut, summary="Xác nhận đặt bàn")
def confirm_reservation(reservation_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return crud.to_out(db, crud.confirm(db, _load(db, reservation_id, user)))


@router.put("/{reservation_id}/table", response_model=ReservationAdminOut, summary="Xếp bàn hoặc đổi bàn")
def assign_table(reservation_id: int, body: AssignTable, user: User = Depends(staff), db: Session = Depends(get_db)):
    return crud.to_out(db, crud.assign_table(db, _load(db, reservation_id, user), body.table_id))


@router.put("/{reservation_id}/cancel", response_model=ReservationAdminOut, summary="Nhân viên huỷ đặt bàn")
def cancel_reservation(reservation_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return crud.to_out(db, crud.cancel(db, _load(db, reservation_id, user)))