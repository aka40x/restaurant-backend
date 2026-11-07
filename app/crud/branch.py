"""CRUD = các hàm đọc/ghi DB cho bảng branches. Router gọi vào đây, không viết SQL trong router."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
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


def create_branch(db: Session, data: BranchCreate) -> Branch:
    branch = Branch(**data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)  # lấy lại id, created_at... do MySQL sinh ra
    return branch


def update_branch(db: Session, branch: Branch, data: BranchUpdate) -> Branch:
    # exclude_unset: chỉ lấy các trường FE thực sự gửi lên
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)
    db.commit()
    db.refresh(branch)
    return branch


def deactivate_branch(db: Session, branch: Branch) -> None:
    # Không xoá thật: order, nhân viên cũ vẫn trỏ tới chi nhánh này. Chỉ đánh dấu ngừng hoạt động.
    branch.is_active = False
    db.commit()
