"""Schema nguyên liệu (M5): hình dạng dữ liệu vào/ra của API nguyên liệu."""
from pydantic import BaseModel, ConfigDict, Field


class IngredientBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Cà chua"])
    unit: str = Field(min_length=1, max_length=20, examples=["g"])  # g, ml, cái...


class IngredientCreate(IngredientBase):
    """Dữ liệu FE gửi lên khi THÊM mới."""


class IngredientUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA. Trường nào không gửi thì giữ nguyên."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)


class IngredientOut(IngredientBase):
    """Dữ liệu API trả về cho FE."""

    model_config = ConfigDict(from_attributes=True)

    id: int