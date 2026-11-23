"""API tuỳ chọn món (size, topping, giá cộng thêm, bắt buộc). Chỉ admin, manager.

    GET    /api/menu-items/{item_id}/options    danh sách tuỳ chọn của 1 món (?only_active=true)
    POST   /api/menu-items/{item_id}/options    thêm tuỳ chọn cho món
    PUT    /api/menu-item-options/{option_id}   sửa
    DELETE /api/menu-item-options/{option_id}   ngừng hoạt động (không xoá thật)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.crud import menu_item as item_crud
from app.crud import menu_item_option as option_crud
from app.db.session import get_db
from app.schemas.menu_item import MenuItemOptionCreate, MenuItemOptionOut, MenuItemOptionUpdate

router = APIRouter(
    tags=["Menu item options"],
    dependencies=[Depends(require_roles("admin", "manager"))],
)


def get_item_or_404(item_id: int, db: Session = Depends(get_db)):
    item = item_crud.get_menu_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={item_id}")
    return item


def get_option_or_404(option_id: int, db: Session = Depends(get_db)):
    option = option_crud.get_option(db, option_id)
    if option is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tuỳ chọn id={option_id}")
    return option


def check_size_or_topping(size: str | None, topping: str | None) -> None:
    """Một tuỳ chọn là size HOẶC topping, không điền cả hai (model: size trống nếu là topping và ngược lại)."""
    if size and topping:
        raise HTTPException(status_code=422, detail="Tuỳ chọn chỉ là size hoặc topping, không điền cả hai")


@router.get("/menu-items/{item_id}/options", response_model=list[MenuItemOptionOut])
def list_options(only_active: bool = False, item=Depends(get_item_or_404), db: Session = Depends(get_db)):
    return option_crud.get_options(db, item.id, only_active=only_active)


@router.post("/menu-items/{item_id}/options", response_model=MenuItemOptionOut, status_code=status.HTTP_201_CREATED)
def create_option(data: MenuItemOptionCreate, item=Depends(get_item_or_404), db: Session = Depends(get_db)):
    if not item.is_active:
        raise HTTPException(status_code=409, detail="Món đã ngừng bán, hãy mở bán lại món trước khi thêm tuỳ chọn")
    check_size_or_topping(data.size, data.topping)
    return option_crud.create_option(db, item.id, data)


@router.put("/menu-item-options/{option_id}", response_model=MenuItemOptionOut)
def update_option(data: MenuItemOptionUpdate, option=Depends(get_option_or_404), db: Session = Depends(get_db)):
    sent = data.model_fields_set
    if "size" in sent or "topping" in sent:  # chỉ kiểm tra khi có đổi size/topping (bật/tắt is_active thì bỏ qua)
        check_size_or_topping(
            data.size if "size" in sent else option.size,
            data.topping if "topping" in sent else option.topping,
        )
    return option_crud.update_option(db, option, data)


@router.delete("/menu-item-options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_option(option=Depends(get_option_or_404), db: Session = Depends(get_db)):
    option_crud.deactivate_option(db, option)