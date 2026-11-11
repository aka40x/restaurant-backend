"""Schema order, món trong order và tuỳ chọn."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Dữ liệu gửi lên ----------
class OrderCreate(BaseModel):
    """Mở order cho một bàn."""

    table_id: int
    reservation_id: int | None = Field(default=None, description="Gắn với đặt bàn nếu khách có đặt trước")
    note: str | None = Field(default=None, max_length=255)


class OrderItemCreate(BaseModel):
    """Gọi thêm một món."""

    menu_item_id: int
    quantity: int = Field(default=1, ge=1, le=99)
    note: str | None = Field(default=None, max_length=255, examples=["Ít cay"])
    option_ids: list[int] = Field(default_factory=list, description="id các tuỳ chọn (size, topping) của món này")


class OrderItemUpdate(BaseModel):
    """Sửa món (chỉ khi món còn ở trạng thái chờ). Trường nào không gửi thì giữ nguyên.

    option_ids: không gửi = giữ nguyên tuỳ chọn; gửi [] = bỏ hết tuỳ chọn; gửi danh sách = thay bằng danh sách đó.
    """

    quantity: int | None = Field(default=None, ge=1, le=99)
    note: str | None = Field(default=None, max_length=255)
    option_ids: list[int] | None = None

class ItemStatusUpdate(BaseModel):
    status: Literal["cooking", "done", "served"]

# ---------- Dữ liệu trả về ----------
class OrderItemOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    option_id: int
    name: str
    extra_price: Decimal


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    menu_item_name: str
    quantity: int
    unit_price: Decimal  # giá món lúc gọi
    note: str | None
    status: str  # pending / cooking / done / served / cancelled
    sent_at: datetime | None  # None = chưa gửi bếp
    options: list[OrderItemOptionOut]
    line_total: Decimal  # (giá món + tuỳ chọn) x số lượng


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    table_id: int
    reservation_id: int | None
    waiter_id: int
    status: str  # open / sent / served / paid / cancelled
    note: str | None
    created_at: datetime
    closed_at: datetime | None


class OrderDetailOut(OrderOut):
    """Order kèm danh sách món và tạm tính."""

    items: list[OrderItemOut]
    subtotal: Decimal  # tạm tính, không gồm món đã huỷ

class KitchenItemOut(BaseModel):
    """Một dòng trong màn hình bếp / ra món."""
    id: int
    order_id: int
    table_number: str
    menu_item_name: str
    quantity: int
    note: str | None
    status: str  # pending / cooking / done
    options: list[str]
    sent_at: datetime