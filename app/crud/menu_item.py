"""CRUD bảng menu_items."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.schemas.menu_item import MenuItemCreate, MenuItemUpdate


def get_menu_items(
    db: Session,
    keyword: str | None = None,
    category_id: int | None = None,
    only_active: bool = False,
    only_available: bool = False,
) -> list[MenuItem]:
    query = select(MenuItem).order_by(MenuItem.id)
    if keyword:
        query = query.where(MenuItem.name.contains(keyword))
    if category_id is not None:
        query = query.where(MenuItem.category_id == category_id)
    if only_active:
        query = query.where(MenuItem.is_active.is_(True))
    if only_available:
        query = query.where(MenuItem.is_available.is_(True))
    return list(db.scalars(query))


def get_menu_item(db: Session, item_id: int) -> MenuItem | None:
    return db.get(MenuItem, item_id)


def create_menu_item(db: Session, data: MenuItemCreate) -> MenuItem:
    item = MenuItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_menu_item(db: Session, item: MenuItem, data: MenuItemUpdate) -> MenuItem:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def set_availability(db: Session, item: MenuItem, is_available: bool) -> MenuItem:
    item.is_available = is_available  # bật/tắt còn món (hết món thì khách không thấy)
    db.commit()
    db.refresh(item)
    return item


def deactivate_menu_item(db: Session, item: MenuItem) -> None:
    # Không xoá thật: đơn hàng cũ vẫn trỏ tới món này
    item.is_active = False
    db.commit()