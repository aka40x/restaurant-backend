"""API order và gọi món. Đường dẫn đầy đủ: /api/orders

    POST   /api/orders                      mở order cho 1 bàn (waiter, manager)
    GET    /api/orders                      danh sách order (?table_id=, ?status=, ?branch_id=)
    GET    /api/orders/{id}                 chi tiết order: món, tuỳ chọn, tạm tính
    POST   /api/orders/{id}/items           gọi thêm món (kèm option_ids)
    PUT    /api/orders/{id}/items/{item_id} sửa số lượng / ghi chú / tuỳ chọn của món (chỉ khi món còn chờ)
    DELETE /api/orders/{id}/items/{item_id} huỷ món (chỉ khi món còn chờ)

Mọi API cần đăng nhập. Nhân viên chỉ thấy và thao tác order của chi nhánh mình (admin thấy tất cả).
Mở order, gọi / sửa / huỷ món: waiter và manager (admin luôn được). Xem: mọi nhân viên của chi nhánh.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, WAITER, check_branch_access, get_current_user, require_roles, resolve_branch_id
from app.core.realtime import publish_item_status, publish_order_changed, publish_order_sent
from app.crud import order as order_crud
from app.db.session import get_db
from app.models.order_item import ITEM_PENDING
from app.models.user import User
from app.schemas.order import (
    ItemStatusUpdate,
    OrderCreate,
    OrderDetailOut,
    OrderItemCreate,
    OrderItemUpdate,
    OrderOut,
    OrderMerge,
    OrderSplit,
    OrderSplitOut,
    OrderTransfer,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

can_order = Depends(require_roles(WAITER, MANAGER))


def get_order_or_404(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_crud.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy order id={order_id}")
    check_branch_access(user, order.branch_id)  # order của chi nhánh khác -> 403
    return order


@router.post("", response_model=OrderDetailOut, status_code=status.HTTP_201_CREATED, dependencies=[can_order])
def open_order(data: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return order_crud.open_order(db, user, data)


@router.get("", response_model=list[OrderOut])
def list_orders(
    table_id: int | None = None,
    status: str | None = None,
    branch_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = resolve_branch_id(user, branch_id)  # admin chọn tuỳ ý, nhân viên chỉ chi nhánh mình
    return order_crud.get_orders(db, branch_id=branch_id, table_id=table_id, status=status)


@router.get("/{order_id}", response_model=OrderDetailOut)
def get_order(order=Depends(get_order_or_404)):
    return order


@router.post(
    "/{order_id}/items", response_model=OrderDetailOut, status_code=status.HTTP_201_CREATED, dependencies=[can_order]
)
def add_item(data: OrderItemCreate, order=Depends(get_order_or_404), db: Session = Depends(get_db)):
    return order_crud.add_item(db, order, data)


@router.put("/{order_id}/items/{item_id}", response_model=OrderDetailOut, dependencies=[can_order])
def update_item(item_id: int, data: OrderItemUpdate, order=Depends(get_order_or_404), db: Session = Depends(get_db)):
    return order_crud.update_item(db, order, item_id, data)


@router.delete("/{order_id}/items/{item_id}", response_model=OrderDetailOut, dependencies=[can_order])
def cancel_item(item_id: int, order=Depends(get_order_or_404), db: Session = Depends(get_db)):
    return order_crud.cancel_item(db, order, item_id)

@router.post("/{order_id}/send-to-kitchen", response_model=OrderDetailOut, dependencies=[can_order])
def send_to_kitchen(order=Depends(get_order_or_404), db: Session = Depends(get_db)):
    sent_ids = [i.id for i in order.items if i.status == ITEM_PENDING and i.sent_at is None]  # các món sắp được gửi bếp
    order = order_crud.send_to_kitchen(db, order)
    publish_order_sent(db, order, sent_ids)  # báo realtime: bếp thấy món mới ngay
    return order


# Quyền (bếp hay phục vụ) được kiểm tra trong crud vì phụ thuộc trạng thái đích
@router.put("/{order_id}/items/{item_id}/status", response_model=OrderDetailOut)
def update_item_status(
    item_id: int,
    data: ItemStatusUpdate,
    order=Depends(get_order_or_404),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = order_crud.update_item_status(db, user, order, item_id, data.status)
    item = next(i for i in order.items if i.id == item_id)
    publish_item_status(db, order, item)  # báo realtime: bếp nhận / nấu xong (báo phục vụ) / đã ra món
    return order
@router.post("/{order_id}/transfer", response_model=OrderDetailOut, dependencies=[can_order])
def transfer_order(data: OrderTransfer, order=Depends(get_order_or_404), db: Session = Depends(get_db)):
    from_table_id = order.table_id
    order = order_crud.transfer_order(db, order, data.table_id)
    publish_order_changed(db, "transfer", order, from_table_id=from_table_id)  # bếp thấy thẻ món đổi bàn ngay
    return order


@router.post("/{order_id}/merge", response_model=OrderDetailOut, dependencies=[can_order])
def merge_orders(
    data: OrderMerge, order=Depends(get_order_or_404), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    order, source = order_crud.merge_orders(db, user, order, data.source_order_id)
    publish_order_changed(db, "merge", order, other=source)
    return order


@router.post("/{order_id}/split", response_model=OrderSplitOut, status_code=status.HTTP_201_CREATED, dependencies=[can_order])
def split_order(data: OrderSplit, order=Depends(get_order_or_404), db: Session = Depends(get_db)):
    order, new_order = order_crud.split_order(db, order, data)
    publish_order_changed(db, "split", order, other=new_order)
    return {"source_order": order, "new_order": new_order}  # FastAPI đổi 2 order này sang OrderSplitOut