"""API công thức món (M5). Đường dẫn đầy đủ: /api/menu-items/{id}/recipe

    GET /api/menu-items/{id}/recipe   xem công thức của món (items rỗng = chưa có công thức)
    PUT /api/menu-items/{id}/recipe   thay toàn bộ công thức: gửi danh sách {ingredient_id, quantity_needed}

Quyền: manager và admin. Món ngừng bán vẫn giữ công thức để báo cáo cũ không mất dữ liệu.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, require_roles
from app.crud import recipe as recipe_crud
from app.db.session import get_db
from app.models.menu_item import MenuItem
from app.schemas.recipe import RecipeUpdate
from app.schemas.stock import RecipeDetailOut

router = APIRouter(prefix="/menu-items", tags=["Recipes"], dependencies=[Depends(require_roles(MANAGER))])


def get_menu_item_or_404(menu_item_id: int, db: Session = Depends(get_db)):
    menu_item = db.get(MenuItem, menu_item_id)
    if menu_item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={menu_item_id}")
    return menu_item


@router.get("/{menu_item_id}/recipe", response_model=RecipeDetailOut)
def get_recipe(menu_item=Depends(get_menu_item_or_404), db: Session = Depends(get_db)):
    return recipe_crud.get_recipe(db, menu_item.id)


@router.put("/{menu_item_id}/recipe", response_model=RecipeDetailOut)
def replace_recipe(data: RecipeUpdate, menu_item=Depends(get_menu_item_or_404), db: Session = Depends(get_db)):
    return recipe_crud.replace_recipe(db, menu_item.id, data)
