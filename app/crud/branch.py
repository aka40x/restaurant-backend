"""CRUD = các hàm đọc/ghi DB cho bảng branches. Router gọi vào đây, không viết SQL trong router."""
import re

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.order import ORDER_ACTIVE_STATUSES, Order
from app.schemas.branch import BranchCreate, BranchUpdate


def get_branches(
    db: Session, keyword: str | None = None, only_active: bool = False, branch_id: int | None = None
) -> list[Branch]:
    query = select(Branch).order_by(Branch.id)
    if branch_id is not None:  # giới hạn theo chi nhánh của nhân viên
        query = query.where(Branch.id == branch_id)
    if keyword:
        query = query.where(Branch.name.contains(keyword))
    if only_active:
        query = query.where(Branch.is_active.is_(True))
    return list(db.scalars(query))


def get_branch(db: Session, branch_id: int) -> Branch | None:
    return db.get(Branch, branch_id)


def _ensure_valid_phone(phone: str | None) -> None:
    """Số điện thoại (không bắt buộc): 6-20 ký tự gồm số, khoảng trắng và + - . ( )"""
    if phone is not None and not re.fullmatch(r"[0-9+\-. ()]{6,20}", phone):
        raise HTTPException(status_code=400, detail="Số điện thoại không hợp lệ (chỉ gồm số, 6-20 ký tự)")


def _ensure_name_unique(db: Session, name: str, exclude_id: int | None = None) -> None:
    """Tên chi nhánh không được trùng (không phân biệt hoa thường)."""
    query = select(Branch.id).where(func.lower(Branch.name) == name.lower())
    if exclude_id is not None:
        query = query.where(Branch.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=f"Đã có chi nhánh tên '{name}'")


def _ensure_can_deactivate(db: Session, branch: Branch) -> None:
    """Còn order chưa thanh toán thì chưa được ngừng hoạt động chi nhánh."""
    open_orders = db.scalar(
        select(func.count()).select_from(Order).where(Order.branch_id == branch.id, Order.status.in_(ORDER_ACTIVE_STATUSES))
    )
    if open_orders:
        raise HTTPException(
            status_code=409, detail=f"Chi nhánh còn {open_orders} order chưa thanh toán, không thể ngừng hoạt động"
        )


def create_branch(db: Session, data: BranchCreate) -> Branch:
    _ensure_name_unique(db, data.name)
    _ensure_valid_phone(data.phone)
    if data.open_time >= data.close_time:
        raise HTTPException(status_code=400, detail="Giờ mở cửa phải trước giờ đóng cửa")
    branch = Branch(**data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)  # lấy lại id, created_at... do MySQL sinh ra
    return branch


def update_branch(db: Session, branch: Branch, data: BranchUpdate) -> Branch:
    # exclude_unset: chỉ lấy các trường FE thực sự gửi lên
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "address", "open_time", "close_time", "is_active"):  # các cột này không được null
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"Trường '{field}' không được để trống")
    if "name" in changes:
        _ensure_name_unique(db, changes["name"], exclude_id=branch.id)
    if "phone" in changes:
        _ensure_valid_phone(changes["phone"])
    # Giờ mở/đóng sau khi sửa (gộp giá trị mới với giá trị cũ) vẫn phải hợp lệ
    if changes.get("open_time", branch.open_time) >= changes.get("close_time", branch.close_time):
        raise HTTPException(status_code=400, detail="Giờ mở cửa phải trước giờ đóng cửa")
    if changes.get("is_active") is False and branch.is_active:
        _ensure_can_deactivate(db, branch)
    for field, value in changes.items():
        setattr(branch, field, value)
    db.commit()
    db.refresh(branch)
    return branch


def deactivate_branch(db: Session, branch: Branch) -> None:
    # Không xoá thật: order, nhân viên cũ vẫn trỏ tới chi nhánh này. Chỉ đánh dấu ngừng hoạt động.
    if branch.is_active:
        _ensure_can_deactivate(db, branch)
    branch.is_active = False
    db.commit()