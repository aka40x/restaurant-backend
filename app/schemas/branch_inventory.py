"""Schema tồn kho theo chi nhánh (M5): hình dạng dữ liệu vào/ra của API tồn kho."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    """Dữ liệu FE gửi lên khi THÊM nguyên liệu vào kho một chi nhánh."""

    branch_id: int = Field(ge=1, examples=[1])
    ingredient_id: int = Field(ge=1, examples=[1])
    quantity: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    min_quantity: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)


class InventoryUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA tồn kho. Trường nào không gửi thì giữ nguyên."""

    quantity: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    min_quantity: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class InventoryOut(BaseModel):
    """Dữ liệu API trả về cho FE."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    ingredient_id: int
    quantity: Decimal
    min_quantity: Decimal