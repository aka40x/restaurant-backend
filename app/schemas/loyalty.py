"""Schema điểm thân thiết (task T3C6F1E)."""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

PHONE_PATTERN = r"^0\d{9,10}$"


class EarnRequest(BaseModel):
    """Tích điểm cho một payment đã thanh toán. Số điểm do server tính, FE không gửi."""

    payment_id: int = Field(ge=1, examples=[1])
    phone: str = Field(pattern=PHONE_PATTERN, examples=["0912345678"])
    full_name: str | None = Field(default=None, min_length=1, max_length=100, examples=["Nguyễn Văn Khách"])  # chỉ dùng khi khách chưa có trong hệ thống


class RedeemRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN, examples=["0912345678"])
    points: int = Field(ge=1, examples=[20])


class LoyaltyTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    points: int
    payment_id: int | None
    voucher_id: int | None
    created_at: datetime


class LoyaltyAccountOut(BaseModel):
    """Số dư điểm và lịch sử gần đây của một khách (tra theo SĐT)."""

    customer_id: int
    full_name: str
    phone: str
    balance: int
    history: list[LoyaltyTransactionOut]


class EarnOut(BaseModel):
    customer_id: int
    payment_id: int
    earned: int  # điểm vừa được cộng
    balance: int  # số dư sau khi cộng


class RedeemOut(BaseModel):
    customer_id: int
    spent: int  # điểm đã trừ
    balance: int  # số dư sau khi trừ
    voucher_code: str  # nhập mã này vào ô voucher ở màn hình thanh toán
    discount_value: Decimal
    end_date: date