"""Tác vụ nền: mỗi phút tự đánh dấu không đến cho đặt bàn quá giờ (T3C65F6)."""
import asyncio

from app.crud.reservation_checkin import mark_overdue_no_shows
from app.db.session import SessionLocal

INTERVAL_SECONDS = 60


def _run_once() -> int:
    with SessionLocal() as db:
        return mark_overdue_no_shows(db)


async def _loop() -> None:
    while True:
        try:
            changed = await asyncio.to_thread(_run_once)
            if changed:
                print(f"[no-show] Đã đánh dấu không đến {changed} đặt bàn quá giờ")
        except Exception as error:  # noqa: BLE001 - lỗi DB tạm thời không được làm chết tác vụ nền
            print(f"[no-show] Lỗi: {error}")
        await asyncio.sleep(INTERVAL_SECONDS)


def start_no_show_job() -> "asyncio.Task":
    """Gọi trong lifespan của FastAPI; nhớ .cancel() khi tắt server."""
    return asyncio.create_task(_loop())