"""CRUD + quy tắc nghiệp vụ cho order và món trong order.

Lưu ý: các hàm ở đây ném thẳng HTTPException khi vi phạm quy tắc (hết món, order đã đóng...)
để router gọn; mã lỗi và câu thông báo nằm cả ở một chỗ.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import check_branch_access
from app.models.dining_table import DiningTable
from app.models.menu_item import MenuItem
from app.models.menu_item_option import MenuItemOption
from app.core.deps import ADMIN, KITCHEN, MANAGER, WAITER, check_branch_access
from app.models.order import ORDER_ACTIVE_STATUSES, ORDER_CANCELLED, ORDER_OPEN, ORDER_SENT, ORDER_SERVED, Order
from app.models.order_item import (
    ITEM_CANCELLED,
    ITEM_COOKING,
    ITEM_DONE,
    ITEM_PENDING,
    ITEM_SERVED,
    OrderItem,
)
from app.models.order_item_option import OrderItemOption
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemCreate, OrderItemUpdate, OrderSplit
from sqlalchemy import func, select

# Món chỉ được sửa / huỷ khi còn chờ VÀ chưa gửi bếp (sent_at trống).
EDITABLE_ITEM_STATUSES = (ITEM_PENDING,)

# Trạng thái mới -> (trạng thái hiện tại bắt buộc, vai trò được đổi). Admin luôn được.
ITEM_TRANSITIONS = {
    ITEM_COOKING: (ITEM_PENDING, (KITCHEN, MANAGER)),
    ITEM_DONE: (ITEM_COOKING, (KITCHEN, MANAGER)),
    ITEM_SERVED: (ITEM_DONE, (WAITER, MANAGER)),
}


def _is_editable(item: OrderItem) -> bool:
    return item.status in EDITABLE_ITEM_STATUSES and item.sent_at is None


# ---------- Đọc ----------
def get_orders(
    db: Session, branch_id: int | None = None, table_id: int | None = None, status: str | None = None
) -> list[Order]:
    query = select(Order).order_by(Order.id.desc())
    if branch_id is not None:
        query = query.where(Order.branch_id == branch_id)
    if table_id is not None:
        query = query.where(Order.table_id == table_id)
    if status:
        query = query.where(Order.status == status)
    return list(db.scalars(query))


def get_order(db: Session, order_id: int) -> Order | None:
    return db.get(Order, order_id)


def _get_active_order_of_table(db: Session, table_id: int) -> Order | None:
    return db.scalar(select(Order).where(Order.table_id == table_id, Order.status.in_(ORDER_ACTIVE_STATUSES)))


# ---------- Mở order ----------
def open_order(db: Session, user: User, data: OrderCreate) -> Order:
    table = db.get(DiningTable, data.table_id)
    if table is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bàn id={data.table_id}")
    check_branch_access(user, table.branch_id)  # nhân viên chỉ mở order cho bàn của chi nhánh mình
    if _get_active_order_of_table(db, table.id) is not None:
        raise HTTPException(status_code=409, detail=f"Bàn {table.table_number} đang có order chưa thanh toán")

    order = Order(
        branch_id=table.branch_id,
        table_id=table.id,
        reservation_id=data.reservation_id,
        waiter_id=user.id,
        status=ORDER_OPEN,
        note=data.note,
    )
    table.status = "occupied"  # bàn có khách
    db.add(order)
    try:
        db.commit()
    except IntegrityError:  # reservation_id không tồn tại
        db.rollback()
        raise HTTPException(status_code=400, detail="Đặt bàn (reservation_id) không tồn tại")
    db.refresh(order)
    return order


# ---------- Món trong order ----------
def _ensure_order_editable(order: Order) -> None:
    if order.status not in ORDER_ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="Order đã đóng (đã thanh toán hoặc đã huỷ), không thể sửa món")


def _build_options(db: Session, menu_item: MenuItem, option_ids: list[int]) -> list[OrderItemOption]:
    options: list[OrderItemOption] = []
    for option_id in dict.fromkeys(option_ids):  # bỏ trùng, giữ thứ tự
        option = db.get(MenuItemOption, option_id)
        if option is None or option.menu_item_id != menu_item.id:
            raise HTTPException(status_code=400, detail=f"Tuỳ chọn id={option_id} không thuộc món '{menu_item.name}'")
        options.append(OrderItemOption(option_id=option.id, extra_price=option.extra_price))  # lưu giá lúc gọi
    return options


def _get_item(order: Order, item_id: int) -> OrderItem:
    for item in order.items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={item_id} trong order này")


def add_item(db: Session, order: Order, data: OrderItemCreate) -> Order:
    _ensure_order_editable(order)
    menu_item = db.get(MenuItem, data.menu_item_id)
    if menu_item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={data.menu_item_id}")
    if not menu_item.is_available:
        raise HTTPException(status_code=400, detail=f"Món '{menu_item.name}' đã hết")

    order.items.append(
        OrderItem(
            menu_item_id=menu_item.id,
            quantity=data.quantity,
            unit_price=menu_item.price,  # lưu giá lúc gọi
            note=data.note,
            status=ITEM_PENDING,
            options=_build_options(db, menu_item, data.option_ids),
        )
    )
    if order.status == ORDER_SERVED:  # đã ra hết món mà khách gọi thêm -> có món mới chưa gửi bếp
        order.status = ORDER_OPEN
    db.commit()
    db.refresh(order)
    return order


def update_item(db: Session, order: Order, item_id: int, data: OrderItemUpdate) -> Order:
    _ensure_order_editable(order)
    item = _get_item(order, item_id)
    if not _is_editable(item):
        raise HTTPException(status_code=409, detail="Món đã gửi bếp hoặc đã huỷ, không thể sửa")

    fields = data.model_fields_set
    if data.quantity is not None:
        item.quantity = data.quantity
    if "note" in fields:
        item.note = data.note
    if data.option_ids is not None:
        item.options = _build_options(db, item.menu_item, data.option_ids)  # thay toàn bộ tuỳ chọn
    db.commit()
    db.refresh(order)
    return order


def cancel_item(db: Session, order: Order, item_id: int) -> Order:
    """Huỷ món = đổi trạng thái sang cancelled (không xoá dòng), món huỷ không tính vào tạm tính."""
    _ensure_order_editable(order)
    item = _get_item(order, item_id)
    if item.status == ITEM_CANCELLED:
        raise HTTPException(status_code=409, detail="Món này đã được huỷ trước đó")
    if not _is_editable(item):
        raise HTTPException(status_code=409, detail="Món đã gửi bếp, không thể huỷ")
    item.status = ITEM_CANCELLED
    db.commit()
    db.refresh(order)
    return order

# ---------- Gửi bếp và trạng thái món ----------
def send_to_kitchen(db: Session, order: Order) -> Order:
    """Gửi mọi món mới (đang chờ, chưa gửi) xuống bếp. Gửi nhiều lần được."""
    _ensure_order_editable(order)
    unsent = [i for i in order.items if i.status == ITEM_PENDING and i.sent_at is None]
    if not unsent:
        raise HTTPException(status_code=400, detail="Không có món mới nào để gửi bếp")
    for item in unsent:
        item.sent_at = func.now()
    order.status = ORDER_SENT
    db.commit()
    db.refresh(order)
    return order


def update_item_status(db: Session, user: User, order: Order, item_id: int, new_status: str) -> Order:
    """Bếp: pending -> cooking -> done. Phục vụ: done -> served. Chỉ đi tiến từng bước."""
    _ensure_order_editable(order)
    required_status, allowed_roles = ITEM_TRANSITIONS[new_status]
    if user.role.name != ADMIN and user.role.name not in allowed_roles:
        raise HTTPException(status_code=403, detail="Bạn không có quyền đổi món sang trạng thái này")

    item = _get_item(order, item_id)
    if item.sent_at is None:
        raise HTTPException(status_code=409, detail="Món chưa được gửi bếp")
    if item.status != required_status:
        raise HTTPException(
            status_code=409,
            detail=f"Món đang ở trạng thái '{item.status}', chỉ đổi sang '{new_status}' được khi món đang '{required_status}'",
        )
    item.status = new_status

    # Mọi món (trừ món huỷ) đã ra hết -> order chuyển sang 'served'
    live = [i for i in order.items if i.status != ITEM_CANCELLED]
    if live and all(i.status == ITEM_SERVED for i in live):
        order.status = ORDER_SERVED
    db.commit()
    db.refresh(order)
    return order


def get_kitchen_items(db: Session, branch_id: int | None = None, statuses: list[str] | None = None) -> list[dict]:
    """Hàng đợi bếp: các món ĐÃ gửi bếp của order còn phục vụ, cũ nhất trước."""
    query = (
        select(OrderItem, DiningTable.table_number)
        .join(Order, OrderItem.order_id == Order.id)
        .join(DiningTable, Order.table_id == DiningTable.id)
        .where(Order.status.in_(ORDER_ACTIVE_STATUSES), OrderItem.sent_at.is_not(None))
        .where(OrderItem.status.in_(statuses or (ITEM_PENDING, ITEM_COOKING, ITEM_DONE)))
        .order_by(OrderItem.sent_at, OrderItem.id)
    )
    if branch_id is not None:
        query = query.where(Order.branch_id == branch_id)
    return [
        {
            "id": item.id,
            "order_id": item.order_id,
            "table_number": table_number,
            "menu_item_name": item.menu_item.name,
            "quantity": item.quantity,
            "note": item.note,
            "status": item.status,
            "options": [o.name for o in item.options],
            "sent_at": item.sent_at,
        }
        for item, table_number in db.execute(query)
    ]
# ---------- Chuyển bàn, gộp bàn, tách món ----------
def _lock_free_table(db: Session, branch_id: int, table_id: int) -> DiningTable:
    """Lấy bàn đích (khoá dòng để 2 người không cùng chuyển vào 1 bàn) và kiểm tra bàn đang trống."""
    table = db.scalar(select(DiningTable).where(DiningTable.id == table_id).with_for_update())
    if table is None or not table.is_active:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bàn id={table_id}")
    if table.branch_id != branch_id:
        raise HTTPException(status_code=400, detail=f"Bàn {table.table_number} thuộc chi nhánh khác")
    if table.status == "reserved":
        raise HTTPException(status_code=409, detail=f"Bàn {table.table_number} đang được đặt trước")
    if _get_active_order_of_table(db, table.id) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Bàn {table.table_number} đang có order chưa thanh toán. Muốn dồn vào bàn đó thì dùng gộp bàn",
        )
    return table


def _release_table(db: Session, table_id: int) -> None:
    """Bàn không còn order nào đang phục vụ -> trống."""
    table = db.get(DiningTable, table_id)
    if table is not None:
        table.status = "available"


def _sync_order_status(order: Order) -> None:
    """Tính lại trạng thái order từ các món (dùng sau khi gộp / tách làm đổi danh sách món)."""
    live = [i for i in order.items if i.status != ITEM_CANCELLED]
    if live and all(i.status == ITEM_SERVED for i in live):
        order.status = ORDER_SERVED
    elif any(i.sent_at is not None and i.status != ITEM_SERVED for i in live):
        order.status = ORDER_SENT  # còn món đang ở bếp
    else:
        order.status = ORDER_OPEN  # chưa gửi bếp gì, hoặc đã ra món hết nhưng còn món mới chưa gửi


def transfer_order(db: Session, order: Order, table_id: int) -> Order:
    """Chuyển cả order sang một bàn TRỐNG khác. Bàn cũ về trống, bàn mới có khách."""
    _ensure_order_editable(order)
    if table_id == order.table_id:
        raise HTTPException(status_code=400, detail="Order đang ở bàn này rồi")
    target = _lock_free_table(db, order.branch_id, table_id)
    old_table_id = order.table_id
    order.table_id = target.id
    target.status = "occupied"
    _release_table(db, old_table_id)
    db.commit()
    db.refresh(order)
    return order


def merge_orders(db: Session, user: User, target: Order, source_order_id: int) -> tuple[Order, Order]:
    """Gộp order `source` vào order `target`: mọi món chuyển sang target, source đóng lại, bàn của source trống.

    Trả về (target, source).
    """
    _ensure_order_editable(target)
    if source_order_id == target.id:
        raise HTTPException(status_code=400, detail="Không thể gộp một order vào chính nó")
    source = db.get(Order, source_order_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy order id={source_order_id}")
    check_branch_access(user, source.branch_id)
    if source.branch_id != target.branch_id:
        raise HTTPException(status_code=400, detail="Hai order thuộc hai chi nhánh khác nhau")
    _ensure_order_editable(source)

    for item in list(source.items):
        target.items.append(item)  # đổi chủ: món sang order đích, giữ nguyên trạng thái và giờ gửi bếp
    if target.reservation_id is None:
        target.reservation_id = source.reservation_id
    source.status = ORDER_CANCELLED  # order gốc không còn tiền, chỉ để lại dấu vết
    source.closed_at = func.now()
    source.note = f"Đã gộp vào order #{target.id}"
    if source.table_id != target.table_id:
        _release_table(db, source.table_id)
    target_table = db.get(DiningTable, target.table_id)
    if target_table is not None:
        target_table.status = "occupied"

    db.flush()
    db.expire(target)  # nạp lại danh sách món từ DB rồi mới tính trạng thái
    db.expire(source)
    _sync_order_status(target)
    db.commit()
    db.refresh(target)
    db.refresh(source)
    return target, source


def split_order(db: Session, order: Order, data: OrderSplit) -> tuple[Order, Order]:
    """Tách một số món (hoặc một phần số lượng) sang order MỚI ở một bàn trống khác.

    Mỗi bàn chỉ có 1 order đang phục vụ nên order mới bắt buộc nằm ở bàn khác. Trả về (order gốc, order mới).
    """
    _ensure_order_editable(order)
    item_ids = [entry.item_id for entry in data.items]
    if len(set(item_ids)) != len(item_ids):
        raise HTTPException(status_code=400, detail="Mỗi món chỉ được chọn một lần")

    moves: list[tuple[OrderItem, int]] = []
    for entry in data.items:
        item = _get_item(order, entry.item_id)
        if item.status == ITEM_CANCELLED:
            raise HTTPException(status_code=409, detail=f"Món '{item.menu_item.name}' đã huỷ, không thể tách")
        quantity = entry.quantity if entry.quantity is not None else item.quantity
        if quantity > item.quantity:
            raise HTTPException(
                status_code=400, detail=f"Món '{item.menu_item.name}' chỉ có {item.quantity} phần, không tách được {quantity}"
            )
        moves.append((item, quantity))

    moved = {item.id: quantity for item, quantity in moves}
    stays = [i for i in order.items if i.status != ITEM_CANCELLED and i.quantity - moved.get(i.id, 0) > 0]
    if not stays:
        raise HTTPException(status_code=400, detail="Không thể tách hết món. Muốn dời cả order sang bàn khác thì dùng chuyển bàn")

    target_table = _lock_free_table(db, order.branch_id, data.table_id)
    new_order = Order(
        branch_id=order.branch_id,
        table_id=target_table.id,
        waiter_id=order.waiter_id,
        status=ORDER_OPEN,
        note=data.note or f"Tách từ order #{order.id}",
    )
    db.add(new_order)
    for item, quantity in moves:
        if quantity == item.quantity:
            new_order.items.append(item)  # chuyển nguyên dòng món
        else:  # tách một phần số lượng: dòng cũ giảm, dòng mới có cùng trạng thái, tuỳ chọn, giờ gửi bếp
            item.quantity -= quantity
            new_order.items.append(
                OrderItem(
                    menu_item_id=item.menu_item_id,
                    quantity=quantity,
                    unit_price=item.unit_price,
                    status=item.status,
                    note=item.note,
                    sent_at=item.sent_at,
                    options=[OrderItemOption(option_id=o.option_id, extra_price=o.extra_price) for o in item.options],
                )
            )
    target_table.status = "occupied"

    db.flush()
    db.expire(order)
    db.expire(new_order)
    _sync_order_status(order)
    _sync_order_status(new_order)
    db.commit()
    db.refresh(order)
    db.refresh(new_order)
    return order, new_order