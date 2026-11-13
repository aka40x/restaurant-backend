"""Schema cho API quản lý đặt bàn nội bộ (T3C65C2)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BranchBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TableBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    table_number: str
    area: str | None = None
    capacity: int


class ReservationAdminOut(BaseModel):
    """Một đặt bàn kèm chi nhánh và bàn đã xếp (table = None nếu chưa xếp)."""
    id: int
    code: str
    status: str
    reserved_at: datetime
    party_size: int
    guest_name: str
    guest_phone: str
    note: str | None = None
    branch: BranchBrief
    table: TableBrief | None = None


class AssignTable(BaseModel):
    table_id: int