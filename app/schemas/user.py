"""Schema nhân viên. Mật khẩu chỉ có ở dữ liệu gửi lên, UserOut không có mật khẩu."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.branch import BranchOut

from app.schemas.role import RoleOut

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=100, examples=["Nguyễn Văn A"])
    email: str = Field(max_length=100, pattern=EMAIL_PATTERN, examples=["a@restaurant.com"])
    phone: str | None = Field(default=None, max_length=20, examples=["0901000001"])
    branch_id: int | None = Field(default=None, description="Để trống nếu là admin tổng")
    role_id: int


class UserCreate(UserBase):
    """Dữ liệu FE gửi lên khi THÊM nhân viên."""

    password: str = Field(min_length=8, max_length=72, examples=["Restaurant@123"])
    is_active: bool = True


class UserUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA. Trường nào không gửi thì giữ nguyên."""

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=100, pattern=EMAIL_PATTERN)
    phone: str | None = Field(default=None, max_length=20)
    branch_id: int | None = None
    role_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    is_active: bool | None = None


class UserOut(BaseModel):
    """Dữ liệu API trả về cho FE. Không có mật khẩu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    branch_id: int | None
    role_id: int
    role: RoleOut
    branch: BranchOut | None  # trống nếu là admin tổng
    is_active: bool
    created_at: datetime