"""API hàng đợi bếp: GET /api/kitchen/items (?status=pending&status=cooking, ?branch_id=)"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, resolve_branch_id
from app.crud import order as order_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import KitchenItemOut

router = APIRouter(prefix="/kitchen", tags=["Kitchen"])


@router.get("/items", response_model=list[KitchenItemOut])
def list_kitchen_items(
    status: list[Literal["pending", "cooking", "done"]] | None = Query(default=None),
    branch_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = resolve_branch_id(user, branch_id)
    return order_crud.get_kitchen_items(db, branch_id=branch_id, statuses=status)