from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class OrderItemOptionCreate(BaseModel):
    option_id: int

class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int
    note: Optional[str] = None
    options: List[OrderItemOptionCreate] = []

class OrderCreate(BaseModel):
    branch_id: int
    table_id: int
    reservation_id: Optional[int] = None
    note: Optional[str] = None
    items: List[OrderItemCreate] = []

class OrderItemStatusUpdate(BaseModel):
    status: str # pending, cooking, done, served, cancelled

class OrderResponse(BaseModel):
    id: int
    branch_id: int
    table_id: int
    reservation_id: Optional[int]
    waiter_id: int
    status: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True