from dataclasses import dataclass


@dataclass
class CategoryEntity:
    id: int
    user_id: int
    name: str
    icon: str | None
    parent_id: int | None
    is_system: bool
    category_type: str  # income / expense / both
