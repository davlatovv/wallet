from typing import Literal

from pydantic import BaseModel, Field

from app.domain.entities.category import CategoryEntity

CategoryType = Literal["income", "expense", "both"]


class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: str | None
    parent_id: int | None
    is_system: bool
    category_type: CategoryType

    @classmethod
    def from_entity(cls, c: CategoryEntity) -> "CategoryResponse":
        return cls(id=c.id, name=c.name, icon=c.icon, parent_id=c.parent_id,
                   is_system=c.is_system, category_type=c.category_type)


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=8)
    parent_id: int | None = None
    category_type: CategoryType = "expense"


class UpdateCategoryRequest(BaseModel):
    """Send only what changes; `icon: null` removes the icon."""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=8)
