"""Giới hạn đăng nhập sai: tối đa MAX_FAILS lần trong WINDOW_SECONDS giây cho mỗi email.

Lưu trong RAM của tiến trình (khởi động lại server là xoá; chạy nhiều tiến trình thì mỗi tiến trình đếm riêng).
Đủ để chặn dò mật khẩu cho đồ án; hệ thống thật nên dùng Redis.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

MAX_FAILS = 5
WINDOW_SECONDS = 15 * 60

_fails: dict[str, deque] = defaultdict(deque)


def _purge(key: str, now: float) -> deque:
    attempts = _fails[key]
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    if not attempts:
        _fails.pop(key, None)
    return attempts


def check(key: str) -> None:
    """Gọi TRƯỚC khi kiểm tra mật khẩu. Sai quá nhiều -> 429."""
    now = time.time()
    attempts = _purge(key, now)
    if len(attempts) >= MAX_FAILS:
        wait = int(WINDOW_SECONDS - (now - attempts[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Đăng nhập sai quá nhiều lần, vui lòng thử lại sau {max(1, wait // 60)} phút",
            headers={"Retry-After": str(wait)},
        )


def record_failure(key: str) -> None:
    _fails[key].append(time.time())


def reset(key: str) -> None:
    _fails.pop(key, None)