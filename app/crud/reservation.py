"""CRUD = các hàm đọc/ghi DB cho bảng reservations."""
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dining_table import DiningTable
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate

HOLD_MINUTES = 120  # mỗi đặt bàn giữ bàn 120 phút (đề xuất, nhóm chốt)
ACTIVE_STATUSES = ("pending", "confirmed", "seated")  # các trạng thái đang chiếm bàn
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ O, 0, I, 1 cho khỏi nhầm
CANCELLABLE_STATUSES = ("pending", "confirmed")  # khách chỉ huỷ được khi chưa nhận bàn (BR-05)
 

def generate_code(db: Session) -> str:
    """Sinh mã đặt bàn duy nhất, vd DBK7M2XQ."""
    for _ in range(10):
        code = "DB" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if db.scalar(select(Reservation.id).where(Reservation.code == code)) is None:
            return code
    raise RuntimeError("Không sinh được mã đặt bàn duy nhất")


def find_free_table(
    db: Session, branch_id: int, party_size: int, reserved_at: datetime
) -> DiningTable | None:
    """Tìm bàn nhỏ nhất đủ chỗ và không trùng khung giờ. Không có thì trả None."""
    window_start = reserved_at - timedelta(minutes=HOLD_MINUTES)
    window_end = reserved_at + timedelta(minutes=HOLD_MINUTES)

    # with_for_update: khoá các dòng bàn này đến khi commit, để 2 khách đặt cùng lúc
    # không cùng chiếm 1 bàn
    tables = db.scalars(
        select(DiningTable)
        .where(
            DiningTable.branch_id == branch_id,
            DiningTable.is_active.is_(True),
            DiningTable.capacity >= party_size,
        )
        .order_by(DiningTable.capacity, DiningTable.id)
        .with_for_update()
    ).all()

    for table in tables:
        conflict = db.scalar(
            select(Reservation.id)
            .where(
                Reservation.table_id == table.id,
                Reservation.status.in_(ACTIVE_STATUSES),
                Reservation.reserved_at > window_start,
                Reservation.reserved_at < window_end,
            )
            .limit(1)
        )
        if conflict is None:
            return table
    return None


def create_reservation(
    db: Session, data: ReservationCreate, table: DiningTable, customer_id: int | None
) -> Reservation:
    reservation = Reservation(
        code=generate_code(db),
        branch_id=data.branch_id,
        table_id=table.id,
        customer_id=customer_id,
        guest_name=data.guest_name.strip(),
        guest_phone=data.guest_phone,
        party_size=data.party_size,
        reserved_at=data.reserved_at,
        status="pending",
        note=data.note,
    )
    db.add(reservation)
    db.commit()  # commit cũng nhả khoá bàn
    db.refresh(reservation)
    return reservation

def get_reservation_by_code_phone(
    db: Session, code: str, phone: str, for_update: bool = False
) -> Reservation | None:
    """Tìm đặt bàn theo mã VÀ số điện thoại. for_update=True để khoá dòng khi sắp sửa."""
    query = select(Reservation).where(Reservation.code == code, Reservation.guest_phone == phone)
    if for_update:
        query = query.with_for_update()  # tránh vừa huỷ vừa check-in cùng lúc
    return db.scalar(query)


def cancel_reservation(db: Session, reservation: Reservation) -> Reservation:
    # Giữ nguyên table_id để lưu lịch sử. Bàn vẫn trống vì 'cancelled' không còn chiếm bàn.
    reservation.status = "cancelled"
    db.commit()
    db.refresh(reservation)
    return reservation