"""Thông báo realtime qua WebSocket: gửi sự kiện cho mọi màn hình đang mở cùng chi nhánh.

Các router (viết bằng `def` thường, chạy trong threadpool) chỉ cần gọi:

    from app.core.realtime import publish_order_sent, publish_item_status
    publish_order_sent(db, order, [id các món vừa gửi bếp])
    publish_item_status(db, order, item)

Hub này giữ danh sách kết nối TRONG BỘ NHỚ của 1 tiến trình, nên chạy `uvicorn` mặc định (1 worker) là đủ.
Chạy nhiều worker thì mỗi worker có hub riêng và sự kiện sẽ không tới hết mọi người (cần Redis pub/sub).

Các loại sự kiện gửi xuống màn hình (JSON):
    {"type": "hello", ...}         vừa kết nối thành công
    {"type": "pong"}               trả lời "ping" của client (để client biết kết nối còn sống)
    {"type": "order.sent", ...}    phục vụ vừa gửi món xuống bếp
    {"type": "item.status", ...}   món đổi trạng thái (cooking / done / served)
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.models.dining_table import DiningTable

if TYPE_CHECKING:  # chỉ để IDE hiểu kiểu
    from fastapi import WebSocket

log = logging.getLogger("realtime")


@dataclass(eq=False)  # eq=False: so sánh theo đối tượng, để bỏ vào set được
class Client:
    ws: "WebSocket"
    user_id: int
    role: str
    branch_id: int | None  # None = admin tổng, nhận sự kiện của mọi chi nhánh


class Hub:
    def __init__(self) -> None:
        self.clients: set[Client] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    # ---- Chạy trong event loop (endpoint WebSocket) ----
    async def connect(self, client: Client) -> None:
        self.loop = asyncio.get_running_loop()  # nhớ loop để router đồng bộ gửi sự kiện vào được
        self.clients.add(client)

    def disconnect(self, client: Client) -> None:
        self.clients.discard(client)

    async def _broadcast(self, message: dict[str, Any], branch_id: int | None) -> None:
        targets = [c for c in list(self.clients) if c.branch_id is None or branch_id is None or c.branch_id == branch_id]
        results = await asyncio.gather(*(c.ws.send_json(message) for c in targets), return_exceptions=True)
        for client, result in zip(targets, results):
            if isinstance(result, Exception):  # kết nối đã chết: bỏ đi, client tự kết nối lại
                self.clients.discard(client)

    # ---- Gọi được từ hàm đồng bộ (router `def` chạy trong threadpool) ----
    def publish(self, message: dict[str, Any], branch_id: int | None) -> None:
        """Gửi `message` cho mọi màn hình của chi nhánh `branch_id` (và admin). Không bao giờ ném lỗi ra ngoài."""
        loop = self.loop
        if loop is None or not self.clients:
            return  # chưa ai kết nối
        try:
            future = asyncio.run_coroutine_threadsafe(self._broadcast(message, branch_id), loop)
            future.add_done_callback(_log_failure)
        except RuntimeError:  # loop đã đóng (server đang tắt)
            pass


def _log_failure(future) -> None:
    if not future.cancelled() and future.exception() is not None:
        log.warning("Gửi sự kiện realtime lỗi: %s", future.exception())


hub = Hub()


def _table_name(db, table_id: int) -> str:
    table = db.get(DiningTable, table_id)
    return table.table_number if table else "?"


def _table_number(db, order) -> str:
    return _table_name(db, order.table_id)


def publish_order_sent(db, order, item_ids: list[int]) -> None:
    """Phục vụ vừa bấm 'Gửi bếp': báo cho bếp có món mới."""
    hub.publish(
        {
            "type": "order.sent",
            "order_id": order.id,
            "table_number": _table_number(db, order),
            "item_ids": item_ids,
            "count": len(item_ids),
        },
        order.branch_id,
    )


def publish_item_status(db, order, item) -> None:
    """Món đổi trạng thái: bếp nhận / nấu xong (báo phục vụ mang ra) / đã ra món."""
    hub.publish(
        {
            "type": "item.status",
            "order_id": order.id,
            "item_id": item.id,
            "table_number": _table_number(db, order),
            "menu_item_name": item.menu_item.name,
            "quantity": item.quantity,
            "status": item.status,  # cooking / done / served
        },
        order.branch_id,
    )

def publish_order_changed(db, kind: str, order, from_table_id: int | None = None, other=None) -> None:
    """Order đổi bàn / gộp / tách: màn hình bếp và phục vụ tải lại (tên bàn trên thẻ món đã đổi).

    kind = "transfer" (order sang bàn mới, from_table_id = bàn cũ), "merge" (other = order bị gộp vào `order`),
    "split" (other = order mới tách ra từ `order`).
    """
    message = {"type": "order.changed", "kind": kind, "order_id": order.id, "table_number": _table_name(db, order.table_id)}
    if from_table_id is not None:
        message["from_table_number"] = _table_name(db, from_table_id)
    if other is not None:
        message["other_order_id"] = other.id
        message["other_table_number"] = _table_name(db, other.table_id)
    hub.publish(message, order.branch_id)