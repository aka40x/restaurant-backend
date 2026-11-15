"""API quản lý nhân viên. Đường dẫn đầy đủ: /api/users  (chỉ admin, manager)

    GET  /api/users                 danh sách (?q=tên/email/sđt, ?role_id=, ?branch_id=, ?is_active=)
    GET  /api/users/{id}            chi tiết
    POST /api/users                 thêm nhân viên
    PUT  /api/users/{id}            sửa (họ tên, email, sđt, vai trò, chi nhánh, đặt lại mật khẩu nếu gửi password)
    POST /api/users/{id}/lock       khoá tài khoản (không xoá)
    POST /api/users/{id}/unlock     mở khoá
    GET  /api/roles                 các vai trò được phép gán (cho ô chọn vai trò)

Phân quyền (chi tiết ở crud/user.py):
- admin: toàn quyền, mọi chi nhánh.
- manager: chỉ thấy và quản lý nhân viên chi nhánh mình, chỉ các vai trò phục vụ / thu ngân / bếp.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, check_branch_access, get_current_user, require_roles, resolve_branch_id
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.role import RoleOut
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(tags=["Users"], dependencies=[Depends(require_roles(MANAGER))])  # admin luôn được phép


def get_user_or_404(user_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = user_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy nhân viên id={user_id}")
    check_branch_access(actor, user.branch_id)  # manager xem nhân viên chi nhánh khác (hoặc admin tổng) -> 403
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    q: str | None = None,
    role_id: int | None = None,
    branch_id: int | None = None,
    is_active: bool | None = None,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = resolve_branch_id(actor, branch_id)  # admin chọn tuỳ ý, manager chỉ chi nhánh mình
    return user_crud.get_users(db, branch_id=branch_id, role_id=role_id, keyword=q, is_active=is_active)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user=Depends(get_user_or_404)):
    return user


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_crud.create_user(db, actor, data)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    data: UserUpdate,
    user=Depends(get_user_or_404),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_crud.update_user(db, actor, user, data)


@router.post("/users/{user_id}/lock", response_model=UserOut)
def lock_user(user=Depends(get_user_or_404), actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_crud.set_active(db, actor, user, False)


@router.post("/users/{user_id}/unlock", response_model=UserOut)
def unlock_user(user=Depends(get_user_or_404), actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_crud.set_active(db, actor, user, True)


@router.get("/roles", response_model=list[RoleOut])
def list_roles(actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_crud.get_roles(db, actor)