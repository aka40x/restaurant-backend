"""CRUD bảng menu_item_options (size, topping, giá cộng thêm)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item_option import MenuItemOption
from app.schemas.menu_item import MenuItemOptionCreate, MenuItemOptionUpdate


def get_options(db: Session, menu_item_id: int, only_active: bool = False) -> list[MenuItemOption]:
    query = select(MenuItemOption).where(MenuItemOption.menu_item_id == menu_item_id).order_by(MenuItemOption.id)
    if only_active:
        query = query.where(MenuItemOption.is_active.is_(True))
    return list(db.scalars(query))


def get_option(db: Session, option_id: int) -> MenuItemOption | None:
    return db.get(MenuItemOption, option_id)


def create_option(db: Session, menu_item_id: int, data: MenuItemOptionCreate) -> MenuItemOption:
    option = MenuItemOption(menu_item_id=menu_item_id, **data.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


def update_option(db: Session, option: MenuItemOption, data: MenuItemOptionUpdate) -> MenuItemOption:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(option, field, value)
    db.commit()
    db.refresh(option)
    return option


def deactivate_option(db: Session, option: MenuItemOption) -> None:
    # Không xoá thật: đơn hàng cũ vẫn trỏ tới tuỳ chọn này
    option.is_active = False
    db.commit()