# Backend: Hệ thống quản lý nhà hàng (Nhóm 6)
- Kết nối **MySQL** bằng SQLAlchemy + PyMySQL, cấu hình đọc từ file `.env`
- **CRUD mẫu** cho bảng `branches` (chi nhánh: thêm / xem / sửa / ngừng hoạt động / tìm kiếm)
- `sql/init.sql` tạo sẵn **17 bảng** của cả hệ thống + dữ liệu mẫu (5 vai trò, 2 chi nhánh, 5 tài khoản, menu, bàn, voucher...)
- Endpoint **health-check** `GET /api/health` kiểm tra kết nối DB
- **CORS** đã bật để frontend gọi được
- `docker-compose.yml` chạy MySQL, không cần cài MySQL lên máy
- Trang tài liệu API tự sinh: http://127.0.0.1:8000/docs

## 1. Cần cài trước

| Phần mềm | Ghi chú |
|---|---|
| Python **3.10 trở lên** | https://www.python.org/downloads/ (Windows: tick **Add python.exe to PATH** khi cài) |
| Docker Desktop | Để chạy MySQL. Nếu đã có MySQL / XAMPP thì không cần, xem mục 3b |

Kiểm tra: `python --version` (Mac/Linux: `python3 --version`).

## 2. Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py            # Điểm khởi động: tạo app, bật CORS, gắn các router
│   ├── core/config.py     # Đọc cấu hình từ .env
│   ├── db/session.py      # Kết nối MySQL, hàm get_db()
│   ├── models/            # Model = bảng trong DB (branch.py)
│   ├── schemas/           # Schema = dữ liệu vào/ra của API (branch.py)
│   ├── crud/              # Hàm đọc/ghi DB (branch.py)
│   └── routers/           # Khai báo các API (health.py, branches.py)
├── sql/init.sql           # Tạo bảng + dữ liệu mẫu
├── docker-compose.yml     # Chạy MySQL bằng Docker
├── requirements.txt       # Danh sách thư viện Python
└── .env.example           # Mẫu file cấu hình
```

Một request đi qua các lớp như sau:

```
Frontend --HTTP--> routers/branches.py --> crud/branch.py --> models/branch.py --> MySQL
                   (kiểm tra dữ liệu bằng schemas/branch.py)
```

## 3. Cài đặt và chạy

Mở terminal **trong thư mục `backend/`**.

### 3a. Bật MySQL bằng Docker (khuyên dùng)

```bash
docker compose up -d
```

MySQL chạy ở cổng **3307** trên máy bạn (user `app_user`, mật khẩu `app_password`, database `app_db`). Lần đầu chạy, Docker tự chạy `sql/init.sql` để tạo 17 bảng và dữ liệu mẫu.

Muốn xem dữ liệu bằng MySQL Workbench / DBeaver / TablePlus: kết nối `127.0.0.1`, cổng `3307`, user và mật khẩu như trên.

### 3b. Hoặc dùng MySQL có sẵn / XAMPP

1. Bật MySQL (XAMPP: bấm Start ở dòng MySQL).
2. Mở phpMyAdmin hoặc MySQL Workbench, chạy toàn bộ file `sql/init.sql`.
3. Ở bước 3c, sửa `.env` cho đúng máy bạn, thường là:
   ```
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=        # XAMPP mặc định để trống
   ```

### 3c. Tạo file `.env`

```bash
# Windows
copy .env.example .env
# Mac / Linux
cp .env.example .env
```

### 3d. Tạo môi trường ảo và cài thư viện

```bash
python -m venv .venv
```

Kích hoạt môi trường ảo (làm lại mỗi lần mở terminal mới):

| Hệ điều hành | Lệnh |
|---|---|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows CMD | `.venv\Scripts\activate.bat` |
| Mac / Linux | `source .venv/bin/activate` |

> PowerShell báo lỗi "running scripts is disabled"? Chạy một lần:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Khi đầu dòng terminal hiện `(.venv)` là đã kích hoạt. Cài thư viện:

```bash
pip install -r requirements.txt
```

### 3e. Chạy server

```bash
uvicorn app.main:app --reload
```

Terminal in ra `[DB] Đã kết nối MySQL ...` là thành công. `--reload` giúp server tự khởi động lại mỗi khi bạn lưu code.

Kiểm tra:

- http://127.0.0.1:8000/api/health → `{"status":"ok","database":"connected"}`
- http://127.0.0.1:8000/docs → thử trực tiếp mọi API bằng nút **Try it out**

## 4. Danh sách API mẫu

| Method | URL | Việc làm | Body (JSON) |
|---|---|---|---|
| GET | `/api/health` | Kiểm tra server + DB | |
| GET | `/api/branches` | Danh sách, tìm theo tên `?q=quan`, chỉ đang hoạt động `?only_active=true` | |
| GET | `/api/branches/{id}` | Chi tiết | |
| POST | `/api/branches` | Thêm mới | `{"name": "Chi nhánh Đà Nẵng", "address": "...", "phone": "0236...", "open_time": "10:00", "close_time": "22:00"}` |
| PUT | `/api/branches/{id}` | Sửa (gửi trường nào sửa trường đó) | `{"is_active": true}` |
| DELETE | `/api/branches/{id}` | Ngừng hoạt động (xoá mềm, trả 204) | |

Khi lỗi, API trả về JSON dạng `{"detail": "..."}`. Ví dụ: 404 khi không tìm thấy, 422 khi dữ liệu gửi lên sai.

## 5. Frontend nối với backend thế nào?

- Frontend gọi tới `http://127.0.0.1:8000/api/...` (cấu hình ở `frontend/js/config.js`).
- Trình duyệt chặn web ở địa chỉ khác gọi API nếu backend không cho phép. Đó là **CORS**. Backend đã cho phép bằng `CORS_ORIGINS` trong `.env`:
  - `CORS_ORIGINS=*` cho phép mọi nơi (mặc định, tiện khi học)
  - Khi deploy thật, ghi rõ domain: `CORS_ORIGINS=https://nhom1.example.com`
- Sửa `.env` xong phải **tắt và chạy lại** uvicorn.

## 6. Thêm chức năng mới (vd: bảng `products`)

1. `app/models/product.py`: copy `branch.py`, đổi tên class, `__tablename__` và các cột.
2. `app/models/__init__.py`: thêm `from app.models.product import Product`.
3. `app/schemas/product.py`: copy `schemas/branch.py`, sửa các trường.
4. `app/crud/product.py`: copy `crud/branch.py`, đổi `Branch` thành `Product`.
5. `app/routers/products.py`: copy `routers/branches.py`, đổi `prefix="/products"`.
6. `app/main.py`: thêm `app.include_router(products.router, prefix="/api")`.
7. Chạy lại server. **Bảng mới được tự tạo** khi server khởi động.

> Lưu ý: tự tạo bảng chỉ áp dụng cho bảng **chưa có**. Nếu sửa cột của bảng đã tồn tại, hãy sửa bằng SQL (`ALTER TABLE ...`) hoặc xoá bảng để server tạo lại (mất dữ liệu bảng đó). Nên ghi lại câu SQL vào `sql/` để cả nhóm cùng chạy.

## 7. Lỗi hay gặp

| Lỗi | Cách sửa |
|---|---|
| `[DB] KHÔNG kết nối được MySQL!` / health trả `503` | MySQL chưa bật (`docker compose up -d`, hoặc Start trong XAMPP). Kiểm tra lại `DB_PORT`, `DB_USER`, `DB_PASSWORD` trong `.env` |
| `Access denied for user` | Sai user/mật khẩu trong `.env` |
| `Unknown database 'app_db'` | Chưa chạy `sql/init.sql` (khi dùng XAMPP / MySQL cài tay) |
| `ModuleNotFoundError: No module named 'fastapi'` | Chưa kích hoạt `.venv` hoặc chưa `pip install -r requirements.txt` |
| `Error loading ASGI app. Could not import module "app.main"` | Đang đứng sai thư mục. Phải `cd` vào `backend/` rồi mới chạy uvicorn |
| Cổng 3307 hoặc 8000 đã bị dùng | Đổi cổng: trong `docker-compose.yml` (`"3308:3306"`, nhớ sửa `DB_PORT`), hoặc `uvicorn app.main:app --reload --port 8001` (nhớ sửa `frontend/js/config.js`) |
| Muốn xoá sạch DB và tạo lại từ `init.sql` | `docker compose down -v` rồi `docker compose up -d` |

Tắt MySQL khi không dùng: `docker compose down` (dữ liệu vẫn được giữ).

## 8. Quy ước làm việc của Nhóm 6

**Hai repo riêng:** `backend` (thư mục này) và `frontend`. Dùng **cùng tên nhánh** ở cả 2 repo cho một chức năng, vd `feature/m1-auth`.

**Quy trình git:** không code trực tiếp trên `main`. Tạo nhánh `feature/<module>-<việc>`, commit, push, tạo Pull Request, một bạn khác review rồi mới merge.

**Phân module:** M1 Xác thực / nhân sự / chi nhánh (`branches`, `roles`, `users`) · M2 Menu và bàn · M3 Web khách và đặt bàn · M4 Order và bếp · M5 Thanh toán, kho, báo cáo. Ai làm module nào thì chỉ sửa model/schema/crud/router của module đó; file chung (`main.py`, `models/__init__.py`) chỉ thêm đúng 1 dòng của mình.

**Tài khoản mẫu** (mật khẩu chung `Restaurant@123`): `admin@restaurant.com`, `manager@restaurant.com`, `cashier@restaurant.com`, `waiter@restaurant.com`, `kitchen@restaurant.com`.

**Đổi cấu trúc DB:** sửa `sql/init.sql`, commit, báo cả nhóm. Mỗi người chạy `docker compose down -v` rồi `docker compose up -d` để tạo lại DB (mất dữ liệu local, dữ liệu mẫu được nạp lại).
