"""CRUD công thức món (M5): một món dùng nguyên liệu nào, bao nhiêu cho một phần (bảng recipes)."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeUpdate
from app.schemas.stock import RecipeDetailOut, RecipeItemDetail


def get_recipe(db: Session, menu_item_id: int) -> RecipeDetailOut:
    rows = db.execute(
        select(Recipe, Ingredient)
        .join(Ingredient, Ingredient.id == Recipe.ingredient_id)
        .where(Recipe.menu_item_id == menu_item_id)
        .order_by(Recipe.id)
    ).all()
    items = [
        RecipeItemDetail(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            unit=ingredient.unit,
            quantity_needed=recipe.quantity_needed,
        )
        for recipe, ingredient in rows
    ]
    return RecipeDetailOut(menu_item_id=menu_item_id, items=items)


def replace_recipe(db: Session, menu_item_id: int, data: RecipeUpdate) -> RecipeDetailOut:
    """Thay toàn bộ công thức của món bằng danh sách gửi lên. Gửi danh sách rỗng = xoá công thức."""
    ids = [line.ingredient_id for line in data.items]
    if ids:
        found = set(db.scalars(select(Ingredient.id).where(Ingredient.id.in_(ids))))
        missing = [i for i in ids if i not in found]
        if missing:
            raise HTTPException(status_code=400, detail=f"Không tìm thấy nguyên liệu id={missing[0]}")
    try:
        db.execute(delete(Recipe).where(Recipe.menu_item_id == menu_item_id))
        for line in data.items:
            db.add(
                Recipe(
                    menu_item_id=menu_item_id,
                    ingredient_id=line.ingredient_id,
                    quantity_needed=line.quantity_needed,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_recipe(db, menu_item_id)
