"""API món ăn. Đường dẫn đầy đủ: /api/menu-items  (chỉ admin, manager)

    GET    /api/menu-items                      danh sách (?q=tên, ?category_id=1, ?only_active=true, ?only_available=true)
    GET    /api/menu-items/{id}                 chi tiết
    POST   /api/menu-items                      thêm mới
    PUT    /api/menu-items/{id}                 sửa
    PATCH  /api/menu-items/{id}/availability    bật/tắt còn món
    DELETE /api/menu-items/{id}                 ngừng hoạt động (không xoá thật)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.crud import category as category_crud
from app.crud import menu_item as item_crud
from app.db.session import get_db
from app.schemas.menu_item import MenuItemCreate, MenuItemOut, MenuItemUpdate

router = APIRouter(
    prefix="/menu-items",
    tags=["Menu items"],
    dependencies=[Depends(require_roles("admin", "manager"))],
)


class AvailabilityIn(BaseModel):
    is_available: bool


def get_item_or_404(item_id: int, db: Session = Depends(get_db)):
    item = item_crud.get_menu_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={item_id}")
    return item


def check_category_exists(db: Session, category_id: int) -> None:
    if category_crud.get_category(db, category_id) is None:
        raise HTTPException(status_code=400, detail=f"Danh mục id={category_id} không tồn tại")


@router.get("", response_model=list[MenuItemOut])
def list_menu_items(
    q: str | None = None,
    category_id: int | None = None,
    only_active: bool = False,
    only_available: bool = False,
    db: Session = Depends(get_db),
):
    return item_crud.get_menu_items(
        db, keyword=q, category_id=category_id, only_active=only_active, only_available=only_available
    )


@router.get("/{item_id}", response_model=MenuItemOut)
def get_menu_item(item=Depends(get_item_or_404)):
    return item


@router.post("", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def create_menu_item(data: MenuItemCreate, db: Session = Depends(get_db)):
    check_category_exists(db, data.category_id)
    return item_crud.create_menu_item(db, data)


@router.put("/{item_id}", response_model=MenuItemOut)
def update_menu_item(data: MenuItemUpdate, item=Depends(get_item_or_404), db: Session = Depends(get_db)):
    if data.category_id is not None:
        check_category_exists(db, data.category_id)
    return item_crud.update_menu_item(db, item, data)


@router.patch("/{item_id}/availability", response_model=MenuItemOut)
def change_availability(data: AvailabilityIn, item=Depends(get_item_or_404), db: Session = Depends(get_db)):
    return item_crud.set_availability(db, item, data.is_available)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_menu_item(item=Depends(get_item_or_404), db: Session = Depends(get_db)):
    item_crud.deactivate_menu_item(db, item)