"""CRUD nguyên liệu (M5): hàm đọc/ghi bảng ingredients. Router gọi vào đây, không viết SQL trong router."""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch_inventory import BranchInventory
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.schemas.ingredient import IngredientCreate, IngredientUpdate


def get_ingredients(db: Session, keyword: str | None = None) -> list[Ingredient]:
    query = select(Ingredient).order_by(Ingredient.name)
    if keyword:
        query = query.where(Ingredient.name.contains(keyword))
    return list(db.scalars(query))


def get_ingredient(db: Session, ingredient_id: int) -> Ingredient | None:
    return db.get(Ingredient, ingredient_id)


def _name_taken(db: Session, name: str, exclude_id: int | None = None) -> bool:
    query = select(Ingredient.id).where(func.lower(Ingredient.name) == name.lower())
    if exclude_id is not None:
        query = query.where(Ingredient.id != exclude_id)
    return db.scalar(query) is not None


def create_ingredient(db: Session, data: IngredientCreate) -> Ingredient:
    name = data.name.strip()
    if _name_taken(db, name):
        raise HTTPException(status_code=409, detail=f"Nguyên liệu '{name}' đã tồn tại")
    try:
        ingredient = Ingredient(name=name, unit=data.unit.strip())
        db.add(ingredient)
        db.commit()
        db.refresh(ingredient)
        return ingredient
    except Exception:
        db.rollback()
        raise


def update_ingredient(db: Session, ingredient: Ingredient, data: IngredientUpdate) -> Ingredient:
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()
        if _name_taken(db, changes["name"], exclude_id=ingredient.id):
            raise HTTPException(status_code=409, detail=f"Nguyên liệu '{changes['name']}' đã tồn tại")
    if "unit" in changes and changes["unit"] is not None:
        changes["unit"] = changes["unit"].strip()
    try:
        for field, value in changes.items():
            if value is not None:  # name và unit đều bắt buộc, không cho đặt về rỗng
                setattr(ingredient, field, value)
        db.commit()
        db.refresh(ingredient)
        return ingredient
    except Exception:
        db.rollback()
        raise


def delete_ingredient(db: Session, ingredient: Ingredient) -> None:
    """Bảng ingredients không có cột is_active nên xoá thật. Đang dùng trong công thức hoặc kho thì từ chối."""
    recipe_count = db.scalar(select(func.count()).select_from(Recipe).where(Recipe.ingredient_id == ingredient.id))
    stock_count = db.scalar(
        select(func.count()).select_from(BranchInventory).where(BranchInventory.ingredient_id == ingredient.id)
    )
    if recipe_count or stock_count:
        raise HTTPException(
            status_code=409,
            detail=f"Nguyên liệu đang được dùng trong {recipe_count} công thức và {stock_count} dòng tồn kho, không thể xoá",
        )
    try:
        db.delete(ingredient)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Nguyên liệu đang được dùng, không thể xoá")
    except Exception:
        db.rollback()
        raise
