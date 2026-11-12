from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
 
PHONE_PATTERN = r"^0\d{9,10}$"  # SĐT Việt Nam: bắt đầu bằng 0, 10-11 số
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class CustomerBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=100, examples=["Nguyễn Văn Khách"])
    phone: str = Field(pattern=PHONE_PATTERN, examples=["0912345678"])
    email: str | None = Field(default=None, max_length=100, pattern=EMAIL_PATTERN)


class CustomerCreate(CustomerBase):
    """Dữ liệu gửi lên khi THÊM khách. Mật khẩu không bắt buộc (khách vãng lai)."""

    password: str | None = Field(default=None, min_length=8, max_length=72)


class CustomerUpdate(BaseModel):
    """Trường nào không gửi thì giữ nguyên."""

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    email: str | None = Field(default=None, max_length=100, pattern=EMAIL_PATTERN)


class CustomerOut(CustomerBase):
    """Trả về cho FE. KHÔNG có mật khẩu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime