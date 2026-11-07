from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TableStatus = Literal["available", "occupied", "reserved"]


class DiningTableBase(BaseModel):
    branch_id: int
    table_number: str = Field(min_length=1, max_length=20, examples=["A01"])
    capacity: int = Field(ge=1, examples=[4])  # số ghế
    area: str | None = Field(default=None, max_length=50, examples=["Tầng 1"])
    status: TableStatus = "available"
    is_active: bool = True


class DiningTableCreate(DiningTableBase):
    pass


class DiningTableUpdate(BaseModel):
    table_number: str | None = Field(default=None, min_length=1, max_length=20)
    capacity: int | None = Field(default=None, ge=1)
    area: str | None = Field(default=None, max_length=50)
    status: TableStatus | None = None
    is_active: bool | None = None


class DiningTableOut(DiningTableBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
