"""API chỉ đọc cho màn hình gọi món của phục vụ. Đường dẫn đầy đủ: /api/pos

    GET /api/pos/tables   danh sách bàn của chi nhánh, kèm order đang phục vụ của từng bàn (nếu có)
    GET /api/pos/menu     thực đơn theo danh mục, mỗi món kèm các tuỳ chọn (size, topping)

Mọi nhân viên đã đăng nhập đều gọi được. Nhân viên chỉ thấy chi nhánh của mình (admin thấy tất cả,
có thể lọc ?branch_id=). Router này chỉ ĐỌC, không thay thế CRUD bàn / menu của module M2.
"""
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, resolve_branch_id
from app.db.session import get_db
from app.models.category import Category
from app.models.dining_table import DiningTable
from app.models.menu_item import MenuItem
from app.models.menu_item_option import MenuItemOption
from app.models.order import ORDER_ACTIVE_STATUSES, Order
from app.models.user import User

router = APIRouter(prefix="/pos", tags=["POS"])


class PosTableOut(BaseModel):
    id: int
    branch_id: int
    table_number: str
    capacity: int
    area: str | None
    status: str  # available / occupied / reserved
    active_order_id: int | None  # order chưa thanh toán của bàn, None nếu bàn chưa có order
    active_order_status: str | None


class PosOptionOut(BaseModel):
    id: int
    name: str
    size: str | None
    topping: str | None
    extra_price: Decimal
    is_required: bool


class PosItemOut(BaseModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    image_url: str | None
    is_available: bool
    options: list[PosOptionOut]


class PosCategoryOut(BaseModel):
    id: int
    name: str
    items: list[PosItemOut]


@router.get("/tables", response_model=list[PosTableOut])
def list_tables(branch_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    branch_id = resolve_branch_id(user, branch_id)
    query = select(DiningTable).where(DiningTable.is_active.is_(True)).order_by(DiningTable.branch_id, DiningTable.id)
    if branch_id is not None:
        query = query.where(DiningTable.branch_id == branch_id)
    tables = list(db.scalars(query))

    active_orders = {}
    if tables:
        orders = db.scalars(
            select(Order).where(Order.table_id.in_([t.id for t in tables]), Order.status.in_(ORDER_ACTIVE_STATUSES))
        )
        active_orders = {o.table_id: o for o in orders}

    return [
        PosTableOut(
            id=t.id,
            branch_id=t.branch_id,
            table_number=t.table_number,
            capacity=t.capacity,
            area=t.area,
            status=t.status,
            active_order_id=active_orders[t.id].id if t.id in active_orders else None,
            active_order_status=active_orders[t.id].status if t.id in active_orders else None,
        )
        for t in tables
    ]


@router.get("/menu", response_model=list[PosCategoryOut])
def get_menu(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    categories = list(
        db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id))
    )
    items = list(db.scalars(select(MenuItem).where(MenuItem.is_active.is_(True)).order_by(MenuItem.id)))
    options = db.scalars(select(MenuItemOption).where(MenuItemOption.is_active.is_(True)).order_by(MenuItemOption.id))

    options_by_item = defaultdict(list)
    for o in options:
        options_by_item[o.menu_item_id].append(
            PosOptionOut(
                id=o.id, name=o.name, size=o.size, topping=o.topping, extra_price=o.extra_price, is_required=o.is_required
            )
        )
    items_by_category = defaultdict(list)
    for i in items:
        items_by_category[i.category_id].append(
            PosItemOut(
                id=i.id,
                name=i.name,
                description=i.description,
                price=i.price,
                image_url=i.image_url,
                is_available=i.is_available,
                options=options_by_item[i.id],
            )
        )
    return [PosCategoryOut(id=c.id, name=c.name, items=items_by_category[c.id]) for c in categories]