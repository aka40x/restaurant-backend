"""API nguyên liệu (M5). Đường dẫn đầy đủ: /api/ingredients

    GET    /api/ingredients          danh sách (tìm theo tên: ?q=bot)
    POST   /api/ingredients          thêm mới (tên, đơn vị)
    PUT    /api/ingredients/{id}     sửa (gửi trường nào sửa trường đó)
    DELETE /api/ingredients/{id}     xoá (từ chối nếu đang dùng trong công thức hoặc kho)

Quyền: manager và admin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import MANAGER, require_roles
from app.crud import ingredient as ingredient_crud
from app.db.session import get_db
from app.schemas.ingredient import IngredientCreate, IngredientOut, IngredientUpdate

router = APIRouter(prefix="/ingredients", tags=["Ingredients"], dependencies=[Depends(require_roles(MANAGER))])


def get_ingredient_or_404(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = ingredient_crud.get_ingredient(db, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy nguyên liệu id={ingredient_id}")
    return ingredient


@router.get("", response_model=list[IngredientOut])
def list_ingredients(q: str | None = None, db: Session = Depends(get_db)):
    return ingredient_crud.get_ingredients(db, keyword=q)


@router.post("", response_model=IngredientOut, status_code=status.HTTP_201_CREATED)
def create_ingredient(data: IngredientCreate, db: Session = Depends(get_db)):
    return ingredient_crud.create_ingredient(db, data)


@router.put("/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(data: IngredientUpdate, ingredient=Depends(get_ingredient_or_404), db: Session = Depends(get_db)):
    return ingredient_crud.update_ingredient(db, ingredient, data)


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient=Depends(get_ingredient_or_404), db: Session = Depends(get_db)):
    ingredient_crud.delete_ingredient(db, ingredient)
