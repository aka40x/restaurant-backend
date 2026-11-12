"""Schema voucher (M5): hình dạng dữ liệu vào/ra của API voucher."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoucherBase(BaseModel):
    code: str = Field(min_length=1, max_length=30, examples=["WELCOME10"])
    discount_type: Literal["percent", "amount"] = Field(examples=["percent"])
    discount_value: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=[10])
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    start_date: date
    end_date: date
    usage_limit: int | None = Field(default=None, ge=1, description="Để trống nếu không giới hạn lượt")


class VoucherCreate(VoucherBase):
    """Dữ liệu FE gửi lên khi THÊM mới. Có kiểm tra ngày và mức giảm."""

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Mã voucher không được để trống")
        return v

    @model_validator(mode="after")
    def check_rules(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date phải lớn hơn hoặc bằng start_date")
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("Voucher giảm theo phần trăm không được vượt quá 100")
        return self


class VoucherUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA. Trường nào không gửi thì giữ nguyên."""

    discount_type: Literal["percent", "amount"] | None = None
    discount_value: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    min_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    is_active: bool | None = None

    @model_validator(mode="after")
    def check_rules(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date phải lớn hơn hoặc bằng start_date")
        if self.discount_type == "percent" and self.discount_value is not None and self.discount_value > 100:
            raise ValueError("Voucher giảm theo phần trăm không được vượt quá 100")
        return self


class VoucherOut(VoucherBase):
    """Dữ liệu API trả về cho FE. Không chạy lại kiểm tra ngày/mức giảm trên dữ liệu đã có trong DB."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    used_count: int
    is_active: bool