from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.branch import BranchOut
from app.schemas.dining_table import DiningTableOut

PHONE_PATTERN = r"^0\d{9,10}$"

ReservationStatus = Literal["pending", "confirmed", "seated", "cancelled", "no_show"]


class ReservationCreate(BaseModel):
    """Khách gửi lên khi ĐẶT BÀN. Mã đặt bàn và trạng thái do server tự sinh, khách không gửi."""

    branch_id: int
    guest_name: str = Field(min_length=1, max_length=100, examples=["Nguyễn Văn Khách"])
    guest_phone: str = Field(pattern=PHONE_PATTERN, examples=["0912345678"])
    party_size: int = Field(ge=1, le=50, examples=[4])
    reserved_at: datetime = Field(examples=["2026-11-20T19:00:00"])
    note: str | None = Field(default=None, max_length=255)


class ReservationUpdate(BaseModel):
    """Nội bộ dùng khi xác nhận / xếp bàn / đổi trạng thái. Trường nào không gửi thì giữ nguyên."""

    table_id: int | None = None
    party_size: int | None = Field(default=None, ge=1, le=50)
    reserved_at: datetime | None = None
    status: ReservationStatus | None = None
    note: str | None = Field(default=None, max_length=255)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    branch_id: int
    table_id: int | None
    customer_id: int | None
    guest_name: str
    guest_phone: str
    party_size: int
    reserved_at: datetime
    status: ReservationStatus
    note: str | None
    created_at: datetime

 
class ReservationDetailOut(ReservationOut):
    """Bản đầy đủ kèm chi nhánh và bàn (dùng cho trang tra cứu / quản lý)."""

    branch: BranchOut
    table: DiningTableOut | None
    
class ReservationLookup(BaseModel):
    """Khách gửi lên khi HUỶ đặt bàn: cần đúng mã và số điện thoại đã đặt."""

    code: str = Field(min_length=1, max_length=20, examples=["DBK7M2XQ"])
    phone: str = Field(pattern=PHONE_PATTERN, examples=["0912345678"])