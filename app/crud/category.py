"""CRUD bảng categories."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def get_categories(db: Session, keyword: str | None = None, only_active: bool = False) -> list[Category]:
    query = select(Category).order_by(Category.sort_order, Category.id)
    if keyword:
        query = query.where(Category.name.contains(keyword))
    if only_active:
        query = query.where(Category.is_active.is_(True))
    return list(db.scalars(query))


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def create_category(db: Session, data: CategoryCreate) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, data: CategoryUpdate) -> Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def deactivate_category(db: Session, category: Category) -> None:
    # Không xoá thật (BR-14): món cũ vẫn trỏ tới danh mục này
    category.is_active = False
    db.commit()