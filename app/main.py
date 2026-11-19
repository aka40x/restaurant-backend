"""Điểm khởi động của backend.

Chạy:  uvicorn app.main:app --reload
Tài liệu API tự sinh: http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app import models  # noqa: F401 - import để SQLAlchemy biết các bảng
from app.core.config import settings
from app.db.session import Base, engine
from app.routers import auth, branches, health, reservations, categories, menu_items, payments, kitchen, orders, reservation_admin, reservation_checkin, menu_item_options, users, ingredients, inventory, recipes, dining_tables, pos, ws
from app.core.no_show_job import start_no_show_job  # phải import SAU routers (tránh vòng import deps <-> user)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tự tạo các bảng còn thiếu khi server khởi động (bảng đã có thì bỏ qua).
    # Lưu ý: create_all KHÔNG sửa bảng đã tồn tại. Đổi cột -> sửa bằng SQL hoặc xoá bảng tạo lại.
    try:
        Base.metadata.create_all(bind=engine)
        print(
            f"[DB] Đã kết nối MySQL {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    except OperationalError as error:
        print("[DB] KHÔNG kết nối được MySQL! Kiểm tra MySQL đã bật chưa và file .env.")
        print(f"[DB] Chi tiết: {error.orig}")
    no_show_job = start_no_show_job()  # tự đánh dấu không đến mỗi phút (T3C65F6)
    yield
    no_show_job.cancel()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS: cho phép trang FE (khác cổng/khác domain) gọi được API này
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mọi API đều bắt đầu bằng /api.
# Thêm router mới thì import ở trên và include ở đây (mỗi người chỉ thêm đúng 1 dòng của module mình).

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(branches.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(kitchen.router, prefix="/api")
app.include_router(reservations.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(menu_items.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(menu_item_options.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(ingredients.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(dining_tables.router, prefix="/api")
app.include_router(reservation_admin.router, prefix="/api")
app.include_router(reservation_checkin.router, prefix="/api")
app.include_router(pos.router, prefix="/api")  # màn hình gọi món: bàn + thực đơn
app.include_router(ws.router, prefix="/api")  # WebSocket: ws://127.0.0.1:8000/api/ws?token=...


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} đang chạy. Xem tài liệu API tại /docs"}