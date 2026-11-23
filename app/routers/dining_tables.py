"""API quản lý bàn theo chi nhánh. Đường dẫn đầy đủ: /api/tables

    GET    /api/tables          danh sách (?branch_id=&q=&area=&only_active=true)
    GET    /api/tables/{id}     chi tiết 1 bàn
    POST   /api/tables          thêm bàn          (admin, manager)
    PUT    /api/tables/{id}     sửa bàn           (admin, manager)
    DELETE /api/tables/{id}     ngừng sử dụng bàn (admin, manager) - xoá mềm, không xoá thật

Phân quyền:
- GET: mọi nhân viên đã đăng nhập (phục vụ cần xem sơ đồ bàn). Admin xem mọi chi nhánh,
       nhân viên khác chỉ thấy bàn của chi nhánh mình.
- POST / PUT / DELETE: admin, manager. Manager chỉ thao tác trên chi nhánh của mình.
Quy tắc: số bàn không trùng trong cùng chi nhánh (BR-03) -> trùng trả 409.
Trạng thái bàn (trống / có khách) do hệ thống tự đổi khi mở order, thanh toán, chuyển bàn nên API này
không cho nhập `status`. Không ngừng bàn đang có order chưa thanh toán hoặc đã được xếp cho đặt bàn
(409), và không giảm số ghế thấp hơn số khách của đặt bàn đã xếp (409).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import (
    MANAGER,
    check_branch_access,
    get_current_user,
    require_roles,
    resolve_branch_id,
)
from app.crud import branch as branch_crud
from app.crud import dining_table as table_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.dining_table import DiningTableCreate, DiningTableOut, DiningTableUpdate

router = APIRouter(prefix="/tables", tags=["Dining tables"])

manage_roles = [Depends(require_roles(MANAGER))]  # admin luôn được phép


def get_table_or_404(table_id: int, db: Session = Depends(get_db)):
    table = table_crud.get_table(db, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bàn id={table_id}")
    return table


def duplicate_error(branch_id: int, table_number: str) -> HTTPException:
    return HTTPException(status_code=409, detail=f"Số bàn '{table_number}' đã tồn tại trong chi nhánh id={branch_id}")


@router.get("", response_model=list[DiningTableOut])
def list_tables(
    branch_id: int | None = None,
    q: str | None = None,
    area: str | None = None,
    only_active: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = resolve_branch_id(user, branch_id)  # nhân viên chỉ xem được chi nhánh mình
    return table_crud.get_tables(db, branch_id=branch_id, keyword=q, area=area, only_active=only_active)


@router.get("/{table_id}", response_model=DiningTableOut)
def get_table(table=Depends(get_table_or_404), user: User = Depends(get_current_user)):
    check_branch_access(user, table.branch_id)
    return table


@router.post("", response_model=DiningTableOut, status_code=status.HTTP_201_CREATED, dependencies=manage_roles)
def create_table(data: DiningTableCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_branch_access(user, data.branch_id)  # manager không được thêm bàn cho chi nhánh khác
    branch = branch_crud.get_branch(db, data.branch_id)
    if branch is None or not branch.is_active:
        raise HTTPException(status_code=400, detail=f"Chi nhánh id={data.branch_id} không tồn tại hoặc đã ngừng hoạt động")
    try:
        return table_crud.create_table(db, data)
    except table_crud.DuplicateTableNumber:
        raise duplicate_error(data.branch_id, data.table_number)


@router.put("/{table_id}", response_model=DiningTableOut, dependencies=manage_roles)
def update_table(
    data: DiningTableUpdate,
    table=Depends(get_table_or_404),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_branch_access(user, table.branch_id)
    # Bỏ tick "Đang sử dụng" cũng là ngừng bàn, nên phải chặn giống nút Ngừng (DELETE) bên dưới
    if data.is_active is False and table.is_active:
        blocker = table_crud.get_deactivate_blocker(db, table)
        if blocker:
            raise HTTPException(status_code=409, detail=blocker)
    if data.capacity is not None and data.capacity < table.capacity:
        blocker = table_crud.get_capacity_blocker(db, table, data.capacity)
        if blocker:
            raise HTTPException(status_code=409, detail=blocker)
    try:
        return table_crud.update_table(db, table, data)
    except table_crud.DuplicateTableNumber:
        raise duplicate_error(table.branch_id, data.table_number)


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=manage_roles)
def deactivate_table(table=Depends(get_table_or_404), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_branch_access(user, table.branch_id)
    if table.is_active:
        blocker = table_crud.get_deactivate_blocker(db, table)
        if blocker:
            raise HTTPException(status_code=409, detail=blocker)
    table_crud.deactivate_table(db, table)