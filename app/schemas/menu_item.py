from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Tuỳ chọn món ----------
class MenuItemOptionBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Size L"])
    size: str | None = Field(default=None, max_length=20, examples=["L"])
    topping: str | None = Field(default=None, max_length=50)
    extra_price: Decimal = Field(default=0, ge=0, max_digits=10, decimal_places=2)
    is_required: bool = False
    is_active: bool = True


class MenuItemOptionCreate(MenuItemOptionBase):
    pass


class MenuItemOptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    size: str | None = Field(default=None, max_length=20)
    topping: str | None = Field(default=None, max_length=50)
    extra_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    is_required: bool | None = None
    is_active: bool | None = None


class MenuItemOptionOut(MenuItemOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int


# ---------- Món ----------
class MenuItemBase(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=150, examples=["Pizza hải sản"])
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)  # giá không âm
    image_url: str | None = Field(default=None, max_length=255)
    is_available: bool = True
    is_active: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    image_url: str | None = Field(default=None, max_length=255)
    is_available: bool | None = None
    is_active: bool | None = None


class MenuItemOut(MenuItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime