"""Tự trừ kho khi món chuyển sang "xong" (M5), căn cứ FR-INV-02.

Cách dùng (gọi từ chỗ đổi trạng thái món sang done của module Order, TRƯỚC khi commit):

    from app.crud.stock import consume_for_dish
    consume_for_dish(db, order.branch_id, item.menu_item_id, item.quantity)
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.stock_rules import amount_needed, apply_consumption
from app.models.branch_inventory import BranchInventory
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe


def consume_for_dish(db: Session, branch_id: int, menu_item_id: int, dish_quantity: int) -> list[dict]:
    """Trừ nguyên liệu theo công thức cho `dish_quantity` phần của món, ở kho của chi nhánh `branch_id`.

    KHÔNG commit: phải gọi trong cùng transaction với việc đổi trạng thái món sang done,
    để hai việc cùng lưu hoặc cùng rollback (không để món xong mà kho chưa trừ, hay ngược lại).

    - Món chưa có công thức: bỏ qua, không báo lỗi.
    - Nguyên liệu chưa có dòng trong kho của chi nhánh: bỏ qua nguyên liệu đó.
    - Trả về danh sách nguyên liệu VỪA rơi xuống dưới mức tối thiểu (rỗng nếu không có).
    """
    recipe_rows = db.execute(
        select(Recipe, Ingredient)
        .join(Ingredient, Ingredient.id == Recipe.ingredient_id)
        .where(Recipe.menu_item_id == menu_item_id)
        .order_by(Recipe.ingredient_id)  # luôn khoá các dòng kho theo cùng một thứ tự để tránh khoá chéo nhau
    ).all()

    became_low = []
    for recipe, ingredient in recipe_rows:
        # Khoá dòng kho khi trừ: hai món xong cùng lúc không đè số của nhau
        inv = db.scalar(
            select(BranchInventory)
            .where(BranchInventory.branch_id == branch_id, BranchInventory.ingredient_id == ingredient.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if inv is None:
            continue
        needed = amount_needed(recipe.quantity_needed, dish_quantity)
        new_quantity, just_became_low = apply_consumption(inv.quantity, inv.min_quantity, needed)
        inv.quantity = new_quantity
        if just_became_low:
            became_low.append(
                {
                    "ingredient_id": ingredient.id,
                    "ingredient_name": ingredient.name,
                    "unit": ingredient.unit,
                    "quantity": new_quantity,
                    "min_quantity": inv.min_quantity,
                }
            )
    return became_low
