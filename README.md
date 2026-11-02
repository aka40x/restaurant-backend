# Restaurant Management System

Đồ án nhóm: hệ thống quản lý nhà hàng, tham khảo website Pizza 4P's.

- **Frontend:** HTML / CSS / JavaScript
- **Backend:** Python + FastAPI
- **Database:** MySQL

## Thành viên và phân công

| # | Thành viên | Module |
|---|------------|--------|
| 1 |            | Auth và nhân sự: JWT, phân quyền, nhân viên, chi nhánh |
| 2 |            | Menu và bàn: danh mục, món, tùy chọn, sơ đồ bàn |
| 3 |            | Web khách và đặt bàn: xem menu/chi nhánh, đặt bàn, khách hàng |
| 4 |            | Order và bếp: order theo bàn, màn hình bếp, WebSocket |
| 5 |            | Thanh toán, kho và báo cáo |

## Cấu trúc thư mục

```
backend/     FastAPI (models, schemas, services, routers)
frontend/    customer/ (web khách), admin/ (trang quản lý), assets/ (css, js dùng chung)
database/    schema.sql (script tạo database và bảng)
```

## Cách chạy dự án

### 1. Clone repo

```bash
git clone <link-repo>
cd restaurant-management
```

### 2. Tạo database

Mở MySQL và chạy file `database/schema.sql`.

### 3. Cài backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### 4. Sửa mật khẩu MySQL

Mở `backend/database.py`, thay `YOUR_PASSWORD` bằng mật khẩu MySQL trên máy của mình. Sau đó chạy một lần (ở thư mục gốc của repo) để Git không đưa thay đổi này vào commit:

```bash
git update-index --skip-worktree backend/database.py
```

### 5. Chạy server

```bash
cd backend
uvicorn main:app --reload
```

Mở http://127.0.0.1:8000/docs để xem Swagger.

### 6. Chạy frontend

Mở thư mục `frontend/` bằng VS Code, cài extension **Live Server**, chuột phải vào `frontend/customer/index.html` chọn **Open with Live Server**.

## Quy ước làm việc nhóm

- Không code trực tiếp trên `main`. Mỗi người một nhánh: `feature/<ten>-<module>`.
- Commit có tiền tố: `feat:`, `fix:`, `chore:`, `docs:`.
- Merge vào `main` qua Pull Request, có ít nhất một người xem.
- Trước khi làm: `git checkout main && git pull`, rồi merge `main` vào nhánh của mình.
- Chỉ sửa file thuộc module của mình. File dùng chung (`main.py`, `database.py`, `responses.py`, `schema.sql`, `api.js`, `style.css`) phải báo trong nhóm trước khi sửa. Riêng `main.py` mỗi người chỉ thêm đúng một dòng `include_router`.

## Quy ước code

- Thư mục số nhiều: `models/`, `schemas/`, `services/`, `routers/`.
- Tên file: `<entity>_model.py`, `<entity>_schema.py`, `<entity>_service.py`, `<entity>_router.py`.
- Mọi API trả về qua `responses.py` (6 trường: statusCode, message, error, data, path, timestamp).
- Dùng `db.rollback()` trong khối `except` khi ghi database.
