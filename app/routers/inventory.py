"""API tồn kho theo chi nhánh (M5). Đường dẫn đầy đủ: /api/inventory

    GET  /api/inventory                  tồn kho (?branch_id= cho admin, ?q= tìm theo tên nguyên liệu)
    GET  /api/inventory/low-stock        các nguyên liệu dưới mức cảnh báo (quantity < min_quantity)
    POST /api/inventory                  thêm nguyên liệu vào kho một chi nhánh (lần đầu nhập)
    PUT  /api/inventory/{id}             điều chỉnh tồn hoặc mức cảnh báo
    POST /api/inventory/{id}/receive     nhập thêm hàng (cộng vào tồn hiện có)

Quyền: manager (chỉ chi nhánh của mình) và admin (mọi chi nhánh).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, check_branch_access, get_current_user, require_roles, resolve_branch_id
from app.crud import inventory as inventory_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.branch_inventory import InventoryCreate, InventoryUpdate
from app.schemas.stock import InventoryDetailOut, InventoryReceive

router = APIRouter(prefix="/inventory", tags=["Inventory"], dependencies=[Depends(require_roles(MANAGER))])


def get_inventory_or_404(inventory_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = inventory_crud.get_inventory_row(db, inventory_id)
    if inv is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy dòng tồn kho id={inventory_id}")
    check_branch_access(user, inv.branch_id)  # kho của chi nhánh khác -> 403
    return inv


@router.get("", response_model=list[InventoryDetailOut])
def list_inventory(
    branch_id: int | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = resolve_branch_id(user, branch_id)  # admin chọn tuỳ ý, manager chỉ chi nhánh mình
    return inventory_crud.get_inventory(db, branch_id, keyword=q)


# Khai báo /low-stock trước các đường dẫn có {id} cho dễ đọc
@router.get("/low-stock", response_model=list[InventoryDetailOut])
def list_low_stock(
    branch_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = resolve_branch_id(user, branch_id)
    return inventory_crud.get_inventory(db, branch_id, low_only=True)


@router.post("", response_model=InventoryDetailOut, status_code=status.HTTP_201_CREATED)
def create_inventory(data: InventoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_branch_access(user, data.branch_id)  # manager chỉ thêm vào kho chi nhánh mình
    return inventory_crud.create_inventory(db, data)


@router.put("/{inventory_id}", response_model=InventoryDetailOut)
def update_inventory(data: InventoryUpdate, inv=Depends(get_inventory_or_404), db: Session = Depends(get_db)):
    return inventory_crud.update_inventory(db, inv, data)


@router.post("/{inventory_id}/receive", response_model=InventoryDetailOut)
def receive_stock(data: InventoryReceive, inv=Depends(get_inventory_or_404), db: Session = Depends(get_db)):
    return inventory_crud.receive_stock(db, inv.id, data.amount)
