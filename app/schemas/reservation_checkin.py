"""Schema cho check-in và đánh dấu không đến (T3C65F6)."""
from app.schemas.reservation_admin import ReservationAdminOut


class CheckInOut(ReservationAdminOut):
    """Kết quả check-in: đặt bàn đã seated kèm id order vừa mở cho bàn."""
    order_id: int