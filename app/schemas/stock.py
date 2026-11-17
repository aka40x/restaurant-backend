"""Schema kho (M5): dữ liệu API trả về kèm tên nguyên liệu, đơn vị và cờ cảnh báo, để FE khỏi phải ghép."""
from decimal import Decimal

from pydantic import BaseModel, Field


class RecipeItemDetail(BaseModel):
    """Một nguyên liệu trong công thức của món."""

    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity_needed: Decimal  # lượng cho một phần món


class RecipeDetailOut(BaseModel):
    """Công thức của một món (items rỗng = món chưa có công thức)."""

    menu_item_id: int
    items: list[RecipeItemDetail]


class InventoryDetailOut(BaseModel):
    """Một dòng tồn kho của chi nhánh, kèm tên nguyên liệu."""

    id: int
    branch_id: int
    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity: Decimal  # tồn hiện tại
    min_quantity: Decimal  # mức cảnh báo
    is_low: bool  # True khi quantity < min_quantity (BR-13)


class InventoryReceive(BaseModel):
    """Dữ liệu FE gửi lên khi NHẬP THÊM hàng vào kho."""

    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=[500])
