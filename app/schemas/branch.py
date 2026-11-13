"""Schema = hình dạng dữ liệu đi vào (request) và đi ra (response) của API chi nhánh.

FastAPI dùng schema để tự kiểm tra dữ liệu: sai kiểu / thiếu trường -> trả lỗi 422.
"""
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


class BranchBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Chi nhánh Quận 1"])
    address: str = Field(min_length=1, max_length=255, examples=["8/15 Lê Thánh Tôn, Quận 1"])
    phone: str | None = Field(default=None, max_length=20, examples=["02812345678"])
    open_time: time = Field(default=time(10, 0), examples=["10:00"])
    close_time: time = Field(default=time(22, 0), examples=["22:00"])
    is_active: bool = True


class BranchCreate(BranchBase):
    """Dữ liệu FE gửi lên khi THÊM mới. Tự cắt khoảng trắng đầu/cuối. (Số điện thoại, giờ mở/đóng được kiểm tra ở crud/branch.py)"""

    model_config = ConfigDict(str_strip_whitespace=True)


class BranchUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA. Trường nào không gửi thì giữ nguyên. (Số điện thoại, giờ mở/đóng được kiểm tra ở crud/branch.py)"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    open_time: time | None = None
    close_time: time | None = None
    is_active: bool | None = None


class BranchOut(BranchBase):
    """Dữ liệu API trả về cho FE."""

    # from_attributes: cho phép đọc thẳng từ object SQLAlchemy (branch.name, branch.address...)
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime