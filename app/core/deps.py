"""Kiểm tra đăng nhập và phân quyền, DÙNG CHUNG cho cả nhóm.

Cách dùng trong router của module mình:

    from app.core.deps import ADMIN, MANAGER, get_current_user, require_roles, get_branch_scope

    # 1) Chỉ cần đăng nhập (vai trò nào cũng được):
    @router.get("/abc")
    def abc(user: User = Depends(get_current_user)): ...

    # 2) Chỉ một số vai trò được gọi (admin luôn được phép):
    @router.post("/abc", dependencies=[Depends(require_roles(MANAGER))])
    def create_abc(...): ...

    # 3) Giới hạn dữ liệu theo chi nhánh: admin xem tất cả, nhân viên chỉ xem chi nhánh mình
    @router.get("/orders")
    def list_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        branch_id = get_branch_scope(user)   # None = admin (xem tất cả), còn lại = id chi nhánh của user
        return order_crud.get_orders(db, branch_id=branch_id)

Mã lỗi: 401 = chưa đăng nhập / token sai hoặc hết hạn, 403 = đã đăng nhập nhưng không đủ quyền.
"""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User

# Tên 5 vai trò (khớp bảng roles). Dùng hằng số này, đừng gõ tay chuỗi "admin"... để khỏi sai chính tả.
ADMIN = "admin"
MANAGER = "manager"
CASHIER = "cashier"
WAITER = "waiter"
KITCHEN = "kitchen"

# Tạo nút "Authorize" trong Swagger (/docs): dán access token vào là test được các API cần đăng nhập
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Có token hợp lệ -> trả User; không gửi token -> trả None; token sai/hết hạn -> 401.

    Dùng cho API công khai nhưng muốn xử lý khác khi là nhân viên (vd danh sách chi nhánh).
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials, "access")  # refresh token không dùng được ở đây
        user = user_crud.get_user(db, int(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _unauthorized("Token không hợp lệ hoặc đã hết hạn")
    if user is None or not user.is_active:
        raise _unauthorized("Tài khoản không tồn tại hoặc đã bị khoá")
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    """Bắt buộc đăng nhập. Chưa gửi token -> 401."""
    if user is None:
        raise _unauthorized("Bạn chưa đăng nhập")
    return user


def require_roles(*roles: str):
    """Chỉ cho các vai trò liệt kê được gọi API (admin luôn được phép). Sai vai trò -> 403.

        dependencies=[Depends(require_roles(MANAGER, CASHIER))]
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.name != ADMIN and user.role.name not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này")
        return user

    return checker


# ---------- Giới hạn theo chi nhánh ----------
def get_branch_scope(user: User) -> int | None:
    """Chi nhánh mà user được phép xem: None = tất cả (admin), còn lại = id chi nhánh của chính user."""
    if user.role.name == ADMIN:
        return None
    if user.branch_id is None:
        # Nhân viên chưa gán chi nhánh: chặn luôn, tuyệt đối không được hiểu là "xem tất cả"
        raise HTTPException(status_code=403, detail="Tài khoản chưa được gán chi nhánh")
    return user.branch_id


def check_branch_access(user: User, branch_id: int) -> None:
    """Dùng khi lấy 1 bản ghi theo id: bản ghi thuộc chi nhánh khác -> 403."""
    scope = get_branch_scope(user)
    if scope is not None and scope != branch_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập dữ liệu của chi nhánh này")


def resolve_branch_id(user: User, requested_branch_id: int | None) -> int | None:
    """Dùng khi API nhận ?branch_id=...: admin chọn tuỳ ý, nhân viên chỉ được chọn chi nhánh mình (hoặc bỏ trống)."""
    scope = get_branch_scope(user)
    if scope is None:
        return requested_branch_id
    if requested_branch_id is not None and requested_branch_id != scope:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập dữ liệu của chi nhánh này")
    return scope