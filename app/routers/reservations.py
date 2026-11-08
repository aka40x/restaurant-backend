"""API đặt bàn. Đường dẫn đầy đủ: /api/reservations

    POST /api/reservations    khách đặt bàn (không cần đăng nhập)

Các task sau sẽ thêm vào router này: tra cứu, huỷ (khách) và quản lý nội bộ.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import branch as branch_crud
from app.crud import customer as customer_crud
from app.crud import reservation as reservation_crud
from app.db.session import get_db
from app.schemas.reservation import ReservationCreate, ReservationDetailOut

router = APIRouter(prefix="/reservations", tags=["Reservations"])

VN_TZ = timezone(timedelta(hours=7))
MIN_ADVANCE_MINUTES = 30  # phải đặt trước ít nhất 30 phút
MAX_ADVANCE_DAYS = 60  # không đặt xa quá 60 ngày


@router.post("", response_model=ReservationDetailOut, status_code=status.HTTP_201_CREATED)
def create_reservation(data: ReservationCreate, db: Session = Depends(get_db)):
    """Khách đặt bàn: kiểm tra chi nhánh, giờ mở cửa, còn bàn phù hợp, rồi sinh mã đặt bàn."""
    branch = branch_crud.get_branch(db, data.branch_id)
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy chi nhánh id={data.branch_id}")

    # Đổi giờ về giờ Việt Nam, bỏ múi giờ (DB lưu DATETIME không múi giờ)
    reserved_at = data.reserved_at
    if reserved_at.tzinfo is not None:
        reserved_at = reserved_at.astimezone(VN_TZ).replace(tzinfo=None)
    now = datetime.now(VN_TZ).replace(tzinfo=None)

    if reserved_at < now + timedelta(minutes=MIN_ADVANCE_MINUTES):
        raise HTTPException(status_code=422, detail=f"Cần đặt bàn trước ít nhất {MIN_ADVANCE_MINUTES} phút")
    if reserved_at > now + timedelta(days=MAX_ADVANCE_DAYS):
        raise HTTPException(status_code=422, detail=f"Chỉ nhận đặt bàn trước tối đa {MAX_ADVANCE_DAYS} ngày")
    if not (branch.open_time <= reserved_at.time() <= branch.close_time):
        raise HTTPException(
            status_code=422,
            detail=f"Chi nhánh mở cửa từ {branch.open_time:%H:%M} đến {branch.close_time:%H:%M}",
        )

    data = data.model_copy(update={"reserved_at": reserved_at})

    table = reservation_crud.find_free_table(db, data.branch_id, data.party_size, reserved_at)
    if table is None:
        raise HTTPException(
            status_code=409,
            detail="Không còn bàn phù hợp vào khung giờ này, vui lòng chọn giờ khác hoặc liên hệ nhà hàng",
        )

    customer = customer_crud.get_customer_by_phone(db, data.guest_phone)  # trống = khách vãng lai
    return reservation_crud.create_reservation(db, data, table, customer.id if customer else None)