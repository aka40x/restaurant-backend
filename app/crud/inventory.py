"""CRUD tồn kho theo chi nhánh (M5): bảng branch_inventories. Nhập thêm hàng, chỉnh tồn, mức cảnh báo."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.branch_inventory import BranchInventory
from app.models.ingredient import Ingredient
from app.schemas.branch_inventory import InventoryCreate, InventoryUpdate
from app.schemas.stock import InventoryDetailOut

MAX_QUANTITY = Decimal("99999999.99")  # giới hạn của DECIMAL(10,2)


def _detail(inv: BranchInventory, ingredient: Ingredient) -> InventoryDetailOut:
    return InventoryDetailOut(
        id=inv.id,
        branch_id=inv.branch_id,
        ingredient_id=inv.ingredient_id,
        ingredient_name=ingredient.name,
        unit=ingredient.unit,
        quantity=inv.quantity,
        min_quantity=inv.min_quantity,
        is_low=inv.quantity < inv.min_quantity,  # BR-13: dưới mức tối thiểu thì cảnh báo
    )


def get_inventory(
    db: Session, branch_id: int | None = None, keyword: str | None = None, low_only: bool = False
) -> list[InventoryDetailOut]:
    """Danh sách tồn kho. branch_id = None thì lấy mọi chi nhánh (chỉ admin gọi như vậy)."""
    query = (
        select(BranchInventory, Ingredient)
        .join(Ingredient, Ingredient.id == BranchInventory.ingredient_id)
        .order_by(BranchInventory.branch_id, Ingredient.name)
    )
    if branch_id is not None:
        query = query.where(BranchInventory.branch_id == branch_id)
    if keyword:
        query = query.where(Ingredient.name.contains(keyword))
    if low_only:
        query = query.where(BranchInventory.quantity < BranchInventory.min_quantity)
    return [_detail(inv, ingredient) for inv, ingredient in db.execute(query).all()]


def get_inventory_row(db: Session, inventory_id: int) -> BranchInventory | None:
    return db.get(BranchInventory, inventory_id)


def create_inventory(db: Session, data: InventoryCreate) -> InventoryDetailOut:
    """Thêm một nguyên liệu vào kho của chi nhánh (lần đầu nhập)."""
    ingredient = db.get(Ingredient, data.ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=400, detail=f"Không tìm thấy nguyên liệu id={data.ingredient_id}")
    if db.get(Branch, data.branch_id) is None:
        raise HTTPException(status_code=400, detail=f"Không tìm thấy chi nhánh id={data.branch_id}")
    existed = db.scalar(
        select(BranchInventory.id).where(
            BranchInventory.branch_id == data.branch_id, BranchInventory.ingredient_id == data.ingredient_id
        )
    )
    if existed is not None:
        raise HTTPException(status_code=409, detail="Chi nhánh này đã có nguyên liệu này trong kho, hãy nhập thêm hoặc sửa tồn")
    try:
        inv = BranchInventory(**data.model_dump())
        db.add(inv)
        db.commit()
        db.refresh(inv)
        return _detail(inv, ingredient)
    except Exception:
        db.rollback()
        raise


def update_inventory(db: Session, inv: BranchInventory, data: InventoryUpdate) -> InventoryDetailOut:
    """Điều chỉnh tồn hoặc mức cảnh báo (gửi trường nào sửa trường đó)."""
    try:
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(inv, field, value)
        db.commit()
        db.refresh(inv)
        return _detail(inv, db.get(Ingredient, inv.ingredient_id))
    except Exception:
        db.rollback()
        raise


def receive_stock(db: Session, inventory_id: int, amount: Decimal) -> InventoryDetailOut:
    """Nhập thêm `amount` vào tồn. Khoá dòng khi cộng để hai người nhập cùng lúc không đè số của nhau."""
    try:
        inv = db.scalar(
            select(BranchInventory)
            .where(BranchInventory.id == inventory_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if inv is None:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dòng tồn kho id={inventory_id}")
        if inv.quantity + amount > MAX_QUANTITY:
            raise HTTPException(status_code=400, detail="Số lượng tồn vượt quá giới hạn cho phép")
        inv.quantity = inv.quantity + amount
        db.commit()
        db.refresh(inv)
        return _detail(inv, db.get(Ingredient, inv.ingredient_id))
    except Exception:
        db.rollback()
        raise
