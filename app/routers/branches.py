"""API CRUD mẫu cho chi nhánh. Đường dẫn đầy đủ: /api/branches

    GET    /api/branches          danh sách (tìm theo tên: ?q=quan, chỉ chi nhánh đang hoạt động: ?only_active=true)
    GET    /api/branches/{id}     chi tiết 1 chi nhánh
    POST   /api/branches          thêm mới (chỉ admin)
    PUT    /api/branches/{id}     sửa (chỉ admin)
    DELETE /api/branches/{id}     ngừng hoạt động, không xoá thật (chỉ admin)

Phân quyền (router này cũng là ví dụ mẫu cho cả nhóm, xem app/core/deps.py):
- GET: khách chưa đăng nhập vẫn xem được, nhưng chỉ thấy chi nhánh đang hoạt động (web khách cần).
       admin thấy tất cả; nhân viên khác chỉ thấy chi nhánh của mình.
- POST / PUT / DELETE: chỉ admin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import ADMIN, check_branch_access, get_branch_scope, get_optional_user, require_roles
from app.crud import branch as branch_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.branch import BranchCreate, BranchOut, BranchUpdate

router = APIRouter(prefix="/branches", tags=["Branches"])


def get_branch_or_404(branch_id: int, db: Session = Depends(get_db)):
    branch = branch_crud.get_branch(db, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy chi nhánh id={branch_id}")
    return branch


@router.get("", response_model=list[BranchOut])
def list_branches(
    q: str | None = None,
    only_active: bool = False,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    branch_id = None
    if user is None:
        only_active = True  # khách chưa đăng nhập chỉ thấy chi nhánh đang hoạt động
    else:
        branch_id = get_branch_scope(user)  # admin: None (tất cả), nhân viên khác: chi nhánh của mình
    return branch_crud.get_branches(db, keyword=q, only_active=only_active, branch_id=branch_id)


@router.get("/{branch_id}", response_model=BranchOut)
def get_branch(branch=Depends(get_branch_or_404), user: User | None = Depends(get_optional_user)):
    if user is None:
        if not branch.is_active:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy chi nhánh id={branch.id}")
    else:
        check_branch_access(user, branch.id)
    return branch


@router.post(
    "", response_model=BranchOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(ADMIN))]
)
def create_branch(data: BranchCreate, db: Session = Depends(get_db)):
    return branch_crud.create_branch(db, data)


@router.put("/{branch_id}", response_model=BranchOut, dependencies=[Depends(require_roles(ADMIN))])
def update_branch(data: BranchUpdate, branch=Depends(get_branch_or_404), db: Session = Depends(get_db)):
    return branch_crud.update_branch(db, branch, data)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(ADMIN))])
def deactivate_branch(branch=Depends(get_branch_or_404), db: Session = Depends(get_db)):
    branch_crud.deactivate_branch(db, branch)