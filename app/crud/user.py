"""CRUD + quy tắc nghiệp vụ cho nhân viên (bảng users).

Phân quyền quản lý nhân viên:
- admin: thêm / sửa / khoá mọi nhân viên, mọi chi nhánh, mọi vai trò (kể cả manager, admin).
- manager: chỉ quản lý nhân viên CHI NHÁNH MÌNH và chỉ các vai trò phục vụ, thu ngân, bếp.
  Không tạo / sửa / khoá được manager khác hay admin (tránh tự nâng quyền).

Các hàm ở đây ném thẳng HTTPException khi vi phạm quy tắc, để router gọn.
"""
import re

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import ADMIN, CASHIER, KITCHEN, WAITER, check_branch_access
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

MANAGER_CAN_ASSIGN = (WAITER, CASHIER, KITCHEN)  # các vai trò manager được quản lý
PHONE_PATTERN = r"[0-9+\-. ()]{6,20}"


# ---------- Đọc ----------
def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_users(
    db: Session,
    branch_id: int | None = None,
    role_id: int | None = None,
    keyword: str | None = None,
    is_active: bool | None = None,
) -> list[User]:
    query = select(User).order_by(User.id)
    if branch_id is not None:  # manager: tự giới hạn ở chi nhánh mình (router truyền vào)
        query = query.where(User.branch_id == branch_id)
    if role_id is not None:
        query = query.where(User.role_id == role_id)
    if keyword:
        like = or_(User.full_name.contains(keyword), User.email.contains(keyword), User.phone.contains(keyword))
        query = query.where(like)
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
    return list(db.scalars(query))


def get_roles(db: Session, actor: User) -> list[Role]:
    """Các vai trò actor được gán cho nhân viên (dùng cho ô chọn vai trò)."""
    query = select(Role).order_by(Role.id)
    if actor.role.name != ADMIN:
        query = query.where(Role.name.in_(MANAGER_CAN_ASSIGN))
    return list(db.scalars(query))


# ---------- Kiểm tra quy tắc ----------
def ensure_can_manage(actor: User, target: User) -> None:
    """actor có được sửa / khoá target không. Sai chi nhánh hoặc sai vai trò -> 403."""
    check_branch_access(actor, target.branch_id)  # manager: khác chi nhánh (hoặc target là admin tổng) -> 403
    if actor.role.name != ADMIN and target.role.name not in MANAGER_CAN_ASSIGN:
        raise HTTPException(status_code=403, detail="Quản lý chỉ được quản lý nhân viên phục vụ, thu ngân và bếp")


def _clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Họ tên không được để trống")
    return value


def _clean_phone(value: str | None) -> str | None:
    value = (value or "").strip() or None
    if value is not None and not re.fullmatch(PHONE_PATTERN, value):
        raise HTTPException(status_code=400, detail="Số điện thoại không hợp lệ (chỉ gồm số, 6-20 ký tự)")
    return value


def _ensure_email_free(db: Session, email: str, exclude_id: int | None = None) -> None:
    query = select(User.id).where(func.lower(User.email) == email)
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=f"Email '{email}' đã được dùng cho tài khoản khác")


def _resolve_role_and_branch(db: Session, actor: User, role_id: int, branch_id: int | None) -> int | None:
    """Kiểm tra vai trò + chi nhánh hợp lệ với quyền của actor, trả về branch_id sẽ lưu."""
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=400, detail=f"Vai trò id={role_id} không tồn tại")

    if actor.role.name != ADMIN:
        if role.name not in MANAGER_CAN_ASSIGN:
            raise HTTPException(status_code=403, detail="Quản lý chỉ được gán vai trò phục vụ, thu ngân hoặc bếp")
        if branch_id is not None and branch_id != actor.branch_id:
            raise HTTPException(status_code=403, detail="Quản lý chỉ được quản lý nhân viên chi nhánh mình")
        return actor.branch_id  # luôn là chi nhánh của manager

    if role.name == ADMIN:
        if branch_id is not None:
            raise HTTPException(status_code=400, detail="Admin tổng không thuộc chi nhánh nào, hãy để trống chi nhánh")
        return None
    if branch_id is None:
        raise HTTPException(status_code=400, detail="Nhân viên phải thuộc một chi nhánh")
    branch = db.get(Branch, branch_id)
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=400, detail=f"Chi nhánh id={branch_id} không tồn tại hoặc đã ngừng hoạt động")
    return branch_id


# ---------- Ghi ----------
def create_user(db: Session, actor: User, data: UserCreate) -> User:
    email = data.email.strip().lower()
    _ensure_email_free(db, email)
    branch_id = _resolve_role_and_branch(db, actor, data.role_id, data.branch_id)
    user = User(
        branch_id=branch_id,
        role_id=data.role_id,
        full_name=_clean_name(data.full_name),
        email=email,
        phone=_clean_phone(data.phone),
        password_hash=hash_password(data.password),
        is_active=data.is_active,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # 2 người thêm cùng email cùng lúc
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Email '{email}' đã được dùng cho tài khoản khác")
    db.refresh(user)
    return user


def update_user(db: Session, actor: User, user: User, data: UserUpdate) -> User:
    ensure_can_manage(actor, user)
    changes = data.model_dump(exclude_unset=True)
    for field in ("full_name", "email", "role_id", "is_active"):  # các cột này không được null
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"Trường '{field}' không được để trống")

    if "full_name" in changes:
        user.full_name = _clean_name(changes["full_name"])
    if "phone" in changes:
        user.phone = _clean_phone(changes["phone"])
    if "email" in changes:
        email = changes["email"].strip().lower()
        _ensure_email_free(db, email, exclude_id=user.id)
        user.email = email

    if "role_id" in changes or "branch_id" in changes:
        new_role_id = changes.get("role_id", user.role_id)
        new_branch_id = changes.get("branch_id", user.branch_id)
        if new_role_id != user.role_id:
            if user.id == actor.id:
                raise HTTPException(status_code=403, detail="Bạn không thể tự đổi vai trò của mình")
        user.branch_id = _resolve_role_and_branch(db, actor, new_role_id, new_branch_id)
        user.role_id = new_role_id
        db.flush()
        db.refresh(user)  # nạp lại user.role mới

    if "password" in changes and changes["password"]:
        user.password_hash = hash_password(changes["password"])
    if "is_active" in changes and changes["is_active"] != user.is_active:
        _apply_active(db, actor, user, changes["is_active"])

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email đã được dùng cho tài khoản khác")
    db.refresh(user)
    return user


def _apply_active(db: Session, actor: User, user: User, active: bool) -> None:
    if not active:
        if user.id == actor.id:
            raise HTTPException(status_code=403, detail="Bạn không thể tự khoá tài khoản của mình")
    user.is_active = active


def set_active(db: Session, actor: User, user: User, active: bool) -> User:
    """Khoá / mở khoá tài khoản. Khoá xong, token cũ của người đó lập tức không dùng được nữa."""
    ensure_can_manage(actor, user)
    _apply_active(db, actor, user, active)
    db.commit()
    db.refresh(user)
    return user