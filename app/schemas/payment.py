"""Schema thanh toán (M5): hình dạng dữ liệu vào/ra của API thanh toán."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentCreate(BaseModel):
    """Dữ liệu FE gửi lên khi THANH TOÁN. cashier_id lấy từ token, không nhận từ FE."""

    order_id: int = Field(ge=1, examples=[1])
    method: Literal["cash", "card", "transfer"] = Field(examples=["cash"])
    voucher_code: str | None = Field(default=None, max_length=30, examples=["WELCOME10"])

    @field_validator("voucher_code")
    @classmethod
    def normalize_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        return v or None


class PaymentOut(BaseModel):
    """Dữ liệu API trả về cho FE."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    cashier_id: int
    voucher_id: int | None
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    method: str
    status: str  # paid / refunded
    paid_at: datetime