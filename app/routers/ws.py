"""WebSocket thông báo realtime. Địa chỉ đầy đủ:

    ws://127.0.0.1:8000/api/ws?token=<access_token>

Trình duyệt không gắn được header Authorization cho WebSocket nên token đi kèm trên đường dẫn (?token=).
Token sai / hết hạn / đã đăng xuất: server vẫn nhận kết nối rồi đóng ngay với mã 4401 để client biết mà làm mới token
(đóng trước khi nhận thì trình duyệt chỉ thấy lỗi chung, không phân biệt được).

Client gửi chữ "ping" mỗi ~25 giây, server trả {"type": "pong"}. Quá 60 giây không nghe gì thì server đóng (mã 4408).
Xem các sự kiện server gửi xuống ở app/core/realtime.py.
"""
import asyncio

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.core.deps import ADMIN
from app.core.realtime import Client, hub
from app.core.security import decode_token
from app.crud import revoked_token as revoked_crud
from app.crud import user as user_crud
from app.db.session import SessionLocal

router = APIRouter(tags=["Realtime"])

IDLE_TIMEOUT_SECONDS = 60
CLOSE_UNAUTHORIZED = 4401
CLOSE_IDLE = 4408


def _authenticate(token: str | None) -> tuple[int, str, int | None] | None:
    """Trả (user_id, vai trò, chi nhánh) nếu token hợp lệ, ngược lại None. Chạy trong threadpool (có gọi DB)."""
    if not token:
        return None
    try:
        payload = decode_token(token, "access")  # refresh token không dùng được ở đây
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
    db = SessionLocal()
    try:
        if revoked_crud.is_revoked(db, payload.get("jti")):  # đã đăng xuất: token bị thu hồi
            return None
        user = user_crud.get_user(db, user_id)
        if user is None or not user.is_active:
            return None
        role = user.role.name
        if role == ADMIN:
            return user.id, role, None  # admin nhận sự kiện của mọi chi nhánh
        if user.branch_id is None:
            return None  # nhân viên chưa gán chi nhánh: không nhận gì cả
        return user.id, role, user.branch_id
    finally:
        db.close()


@router.websocket("/ws")
async def realtime(websocket: WebSocket, token: str | None = None):
    await websocket.accept()
    identity = await run_in_threadpool(_authenticate, token)
    if identity is None:
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="Token không hợp lệ hoặc đã hết hạn")
        return

    client = Client(websocket, *identity)
    await hub.connect(client)
    try:
        await websocket.send_json({"type": "hello", "role": client.role, "branch_id": client.branch_id})
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=IDLE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                await websocket.close(code=CLOSE_IDLE, reason="Quá lâu không có tín hiệu")
                break
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(client)