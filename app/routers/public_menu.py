"""API thực đơn công khai cho web khách (không cần đăng nhập). Đường dẫn đầy đủ: /api/public/...

    GET /api/public/categories    danh mục đang dùng
    GET /api/public/menu-items    món đang bán, thuộc danh mục đang dùng (món tạm hết vẫn trả về, is_available=false)
                                  ?category_id=  ?q=

Chỉ đọc. Thêm/sửa/xoá vẫn dùng /api/categories và /api/menu-items (admin, manager).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import category as category_crud
from app.crud import menu_item as item_crud
from app.db.session import get_db
from app.schemas.category import CategoryOut
from app.schemas.menu_item import MenuItemOut

router = APIRouter(prefix="/public", tags=["Public (khách)"])


@router.get("/categories", response_model=list[CategoryOut])
def public_categories(db: Session = Depends(get_db)):
    return category_crud.get_categories(db, only_active=True)


@router.get("/menu-items", response_model=list[MenuItemOut])
def public_menu_items(
    q: str | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    return item_crud.get_menu_items(
        db, keyword=q, category_id=category_id, only_active=True, only_active_category=True
    )