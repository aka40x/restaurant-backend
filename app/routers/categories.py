"""API danh mục món. Đường dẫn đầy đủ: /api/categories  (chỉ admin, manager)

    GET    /api/categories          danh sách (?q=tên, ?only_active=true)
    GET    /api/categories/{id}     chi tiết
    POST   /api/categories          thêm mới
    PUT    /api/categories/{id}     sửa
    DELETE /api/categories/{id}     ngừng hoạt động (không xoá thật)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.crud import category as category_crud
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    dependencies=[Depends(require_roles("admin", "manager"))],
)


def get_category_or_404(category_id: int, db: Session = Depends(get_db)):
    category = category_crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy danh mục id={category_id}")
    return category


@router.get("", response_model=list[CategoryOut])
def list_categories(q: str | None = None, only_active: bool = False, db: Session = Depends(get_db)):
    return category_crud.get_categories(db, keyword=q, only_active=only_active)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category=Depends(get_category_or_404)):
    return category


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return category_crud.create_category(db, data)


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(data: CategoryUpdate, category=Depends(get_category_or_404), db: Session = Depends(get_db)):
    return category_crud.update_category(db, category, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_category(category=Depends(get_category_or_404), db: Session = Depends(get_db)):
    category_crud.deactivate_category(db, category)