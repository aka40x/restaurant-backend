"""Test API check-in và không đến (task T3C65F6), ghi test log ra file CSV.

Cách dùng:
  1. Bật MySQL và backend:  uvicorn app.main:app --reload
  2. Trong thư mục backend/ (đã kích hoạt .venv) chạy:  python test_t3c65f6.py
  3. Mở file test_log_T3C65F6.csv bằng Excel, đính kèm vào Worklane.

Script tự tìm một bàn trống ở chi nhánh của manager, tạo đặt bàn qua API, và chèn thẳng vào DB vài
đặt bàn "quá giờ" để thử cơ chế tự đánh dấu không đến. Chạy xong script tự xoá dữ liệu test
(đặt bàn, order) và trả bàn về trạng thái trống. Cần chạy trong thư mục backend/.
Tài khoản mẫu: admin@, manager@, kitchen@restaurant.com (mật khẩu Restaurant@123).
"""
import csv
import json
import random
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from sqlalchemy import select

from app import models  # noqa: F401 - để SQLAlchemy biết các bảng
from app.crud.reservation_checkin import mark_overdue_no_shows
from app.db.session import SessionLocal
from app.models.dining_table import DiningTable
from app.models.order import ORDER_ACTIVE_STATUSES, Order
from app.models.reservation import Reservation

BASE = "http://127.0.0.1:8000/api"
LOG_FILE = "test_log_T3C65F6.csv"
PASSWORD = "Restaurant@123"
now = datetime.now()
day = (now + timedelta(days=random.randint(5, 55))).date()
SUFFIX = random.randint(1000, 9999)


def call(method, path, token=None, data=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read() or "null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else None)


def login(name):
    status, data = call("POST", "/auth/login", data={"email": f"{name}@restaurant.com", "password": PASSWORD})
    if status != 200:
        raise SystemExit(f"Không đăng nhập được {name}@restaurant.com (status {status}): {data}")
    return data["access_token"]


manager, kitchen, admin = login("manager"), login("kitchen"), login("admin")
_, me = call("GET", "/auth/me", manager)
BRANCH = me["branch_id"]


def book(hour):
    status, data = call("POST", "/reservations", data={
        "branch_id": BRANCH, "guest_name": "Khách Test", "guest_phone": "0912345678", "party_size": 2,
        "reserved_at": f"{day.isoformat()}T{hour:02d}:00:00", "note": "test T3C65F6"})
    if status != 201:
        raise SystemExit(f"Không tạo được đặt bàn mẫu ({status}): {data}")
    return data["id"]


created_res: list[int] = []
table_id = None
try:
    # ---- chuẩn bị: bàn trống (không order đang mở) của chi nhánh manager ----
    with SessionLocal() as db:
        busy = set(db.scalars(select(Order.table_id).where(Order.status.in_(ORDER_ACTIVE_STATUSES))))
        free = [t for t in db.scalars(select(DiningTable).where(
            DiningTable.branch_id == BRANCH, DiningTable.is_active.is_(True), DiningTable.capacity >= 2))
            if t.id not in busy and t.status != "occupied"]
        if not free:
            raise SystemExit("Không có bàn trống để test, hãy thanh toán / đóng bớt order rồi chạy lại.")
        table_id = free[0].id

    r1, r2 = book(12), book(18)   # r1: để check-in; r2: cùng bàn, giờ khác -> bàn đang bận
    created_res += [r1, r2]

    def db_set(res_id, **fields):
        with SessionLocal() as db:
            rec = db.get(Reservation, res_id)
            for k, v in fields.items():
                setattr(rec, k, v)
            db.commit()

    def db_insert(code, when, status, table=None):
        with SessionLocal() as db:
            rec = Reservation(code=f"T65{SUFFIX}{code}", branch_id=BRANCH, table_id=table, guest_name="Test Quá Giờ",
                              guest_phone="0912345678", party_size=2, reserved_at=when, status=status)
            db.add(rec)
            db.commit()
            created_res.append(rec.id)
            return rec.id

    def db_status(res_id):
        with SessionLocal() as db:
            return db.get(Reservation, res_id).status

    cases = []

    def check(tc, desc, got, expected):
        ok = got == expected
        cases.append((tc, desc, expected, got, "PASS" if ok else "FAIL"))
        print(f"{'PASS' if ok else 'FAIL'}  {tc} {desc}: nhận {got}, mong {expected}")

    code = lambda r: r[0]
    check("TC01", "Không token", code(call("PUT", f"/reservations/{r1}/check-in")), 401)
    check("TC02", "Tài khoản bếp bị chặn", code(call("PUT", f"/reservations/{r1}/check-in", kitchen)), 403)
    check("TC03", "Đặt bàn không tồn tại", code(call("PUT", "/reservations/99999999/check-in", admin)), 404)
    check("TC04", "Check-in khi chưa xác nhận (pending)", code(call("PUT", f"/reservations/{r1}/check-in", manager)), 400)
    call("PUT", f"/reservations/{r1}/confirm", manager)
    db_set(r1, table_id=None)
    check("TC05", "Check-in khi chưa xếp bàn", code(call("PUT", f"/reservations/{r1}/check-in", manager)), 400)
    call("PUT", f"/reservations/{r1}/table", manager, {"table_id": table_id})
    st, res = call("PUT", f"/reservations/{r1}/check-in", manager)
    check("TC06", "Check-in hợp lệ", (st, res and res.get("status")), (200, "seated"))
    order_id = res.get("order_id") if res else None
    st, order = call("GET", f"/orders/{order_id}", manager) if order_id else (0, None)
    check("TC07", "Order được mở, gắn đúng đặt bàn và đúng bàn",
          (st, order and order["status"], order and order["reservation_id"], order and order["table_id"]),
          (200, "open", r1, table_id))
    with SessionLocal() as db:
        table_status = db.get(DiningTable, table_id).status
    check("TC08", "Bàn chuyển sang occupied", table_status, "occupied")
    check("TC09", "Check-in lần hai", code(call("PUT", f"/reservations/{r1}/check-in", manager)), 409)
    call("PUT", f"/reservations/{r2}/confirm", manager)
    db_set(r2, table_id=table_id)
    check("TC10", "Bàn đang có order chưa thanh toán", code(call("PUT", f"/reservations/{r2}/check-in", manager)), 409)
    check("TC11", "Đánh dấu không đến khi chưa tới giờ", code(call("PUT", f"/reservations/{r2}/no-show", manager)), 400)
    check("TC12", "Đánh dấu không đến đặt bàn đã check-in", code(call("PUT", f"/reservations/{r1}/no-show", manager)), 400)
    check("TC13", "Tài khoản bếp đánh dấu không đến", code(call("PUT", f"/reservations/{r2}/no-show", kitchen)), 403)

    late10 = db_insert("A", now - timedelta(minutes=10), "pending")
    st, res = call("PUT", f"/reservations/{late10}/no-show", manager)
    check("TC14", "Nhân viên đánh dấu không đến (đã quá giờ)", (st, res and res.get("status")), (200, "no_show"))

    late31 = db_insert("B", now - timedelta(minutes=31), "pending")
    late29 = db_insert("C", now - timedelta(minutes=29), "confirmed", table_id)
    future = db_insert("D", now + timedelta(hours=1), "confirmed", table_id)
    with SessionLocal() as db:
        mark_overdue_no_shows(db)
    check("TC15", "Tự động: quá giờ 31 phút -> no_show", db_status(late31), "no_show")
    check("TC16", "Tự động: quá giờ 29 phút -> giữ nguyên", db_status(late29), "confirmed")
    check("TC17", "Tự động: chưa tới giờ -> giữ nguyên", db_status(future), "confirmed")
    check("TC18", "Tự động: đặt bàn đã check-in không bị đổi", db_status(r1), "seated")

    late40 = db_insert("E", now - timedelta(minutes=40), "confirmed", table_id)
    check("TC19", "Check-in đặt bàn đã quá giờ 40 phút", code(call("PUT", f"/reservations/{late40}/check-in", manager)), 400)
    check("TC20", "...và đặt bàn đó thành no_show", db_status(late40), "no_show")
finally:
    # ---- dọn dữ liệu test: order -> đặt bàn, trả bàn về trống ----
    with SessionLocal() as db:
        for rec in db.scalars(select(Order).where(Order.reservation_id.in_(created_res or [0]))):
            db.delete(rec)
        db.flush()
        for rec in db.scalars(select(Reservation).where(Reservation.id.in_(created_res or [0]))):
            db.delete(rec)
        if table_id is not None:
            db.get(DiningTable, table_id).status = "available"
        db.commit()

with open(LOG_FILE, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["TEST LOG - T3C65F6 - Check-in và đánh dấu không đến"])
    w.writerow(["Người test: Lê Trung Sơn", f"Chạy lúc: {datetime.now():%H:%M %d/%m/%Y}"])
    w.writerow([])
    w.writerow(["Mã", "Mô tả", "Mong đợi", "Thực tế", "Kết quả"])
    w.writerows(cases)
passed = sum(1 for c in cases if c[4] == "PASS")
print(f"\nKết quả: {passed}/{len(cases)} PASS. Đã ghi {LOG_FILE}")