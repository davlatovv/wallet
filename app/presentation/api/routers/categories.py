from fastapi import APIRouter, Response, status

from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.categories import (
    CategoryResponse, CategoryType, CreateCategoryRequest, UpdateCategoryRequest,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    container: ContainerDep, user_id: CurrentUserId, type: CategoryType | None = None
) -> list[CategoryResponse]:
    """Flat list (roots and children); `type=expense` also returns `both` categories."""
    cats = await container.list_all_categories.execute(user_id, type)
    return [CategoryResponse.from_entity(c) for c in cats]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CreateCategoryRequest, container: ContainerDep, user_id: CurrentUserId
) -> CategoryResponse:
    cat = await container.create_category.execute(
        user_id, body.name, body.icon, body.parent_id, body.category_type
    )
    return CategoryResponse.from_entity(cat)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int, body: UpdateCategoryRequest, container: ContainerDep, user_id: CurrentUserId
) -> CategoryResponse:
    current = await container.get_category.execute(category_id, user_id)
    fields = body.model_fields_set
    cat = await container.rename_category.execute(
        category_id, user_id,
        name=body.name if "name" in fields and body.name is not None else current.name,
        icon=body.icon if "icon" in fields else current.icon,
    )
    return CategoryResponse.from_entity(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int, container: ContainerDep, user_id: CurrentUserId
) -> Response:
    await container.delete_category.execute(category_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
