"""API CRUD mẫu cho chi nhánh. Đường dẫn đầy đủ: /api/branches

    GET    /api/branches          danh sách (tìm theo tên: ?q=quan, chỉ chi nhánh đang hoạt động: ?only_active=true)
    GET    /api/branches/{id}     chi tiết 1 chi nhánh
    POST   /api/branches          thêm mới
    PUT    /api/branches/{id}     sửa (gửi trường nào sửa trường đó)
    DELETE /api/branches/{id}     ngừng hoạt động (không xoá thật)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import branch as branch_crud
from app.db.session import get_db
from app.schemas.branch import BranchCreate, BranchOut, BranchUpdate

router = APIRouter(prefix="/branches", tags=["Branches"])


def get_branch_or_404(branch_id: int, db: Session = Depends(get_db)):
    branch = branch_crud.get_branch(db, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy chi nhánh id={branch_id}")
    return branch


@router.get("", response_model=list[BranchOut])
def list_branches(q: str | None = None, only_active: bool = False, db: Session = Depends(get_db)):
    return branch_crud.get_branches(db, keyword=q, only_active=only_active)


@router.get("/{branch_id}", response_model=BranchOut)
def get_branch(branch=Depends(get_branch_or_404)):
    return branch


@router.post("", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(data: BranchCreate, db: Session = Depends(get_db)):
    return branch_crud.create_branch(db, data)


@router.put("/{branch_id}", response_model=BranchOut)
def update_branch(data: BranchUpdate, branch=Depends(get_branch_or_404), db: Session = Depends(get_db)):
    return branch_crud.update_branch(db, branch, data)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_branch(branch=Depends(get_branch_or_404), db: Session = Depends(get_db)):
    branch_crud.deactivate_branch(db, branch)
