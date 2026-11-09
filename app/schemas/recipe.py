"""Schema công thức (M5): một món dùng nguyên liệu nào, bao nhiêu cho một phần."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipeLine(BaseModel):
    ingredient_id: int = Field(ge=1, examples=[1])
    quantity_needed: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=[200])  # lượng cho một phần món


class RecipeUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA công thức: gửi toàn bộ danh sách nguyên liệu của món."""

    items: list[RecipeLine]

    @field_validator("items")
    @classmethod
    def no_duplicate_ingredient(cls, items: list[RecipeLine]) -> list[RecipeLine]:
        ids = [line.ingredient_id for line in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Một nguyên liệu chỉ được xuất hiện một lần trong công thức")
        return items


class RecipeLineOut(BaseModel):
    """Một dòng công thức API trả về cho FE."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    ingredient_id: int
    quantity_needed: Decimal