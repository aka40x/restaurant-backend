from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Món chính"])
    description: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Dữ liệu FE gửi lên khi THÊM mới."""


class CategoryUpdate(BaseModel):
    """Dữ liệu FE gửi lên khi SỬA. Trường nào không gửi thì giữ nguyên."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int