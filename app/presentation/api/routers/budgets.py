from fastapi import APIRouter, Response, status

from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.budgets import (
    BudgetProgressResponse, BudgetResponse, SetBudgetRequest,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetProgressResponse])
async def list_budgets(container: ContainerDep, user_id: CurrentUserId) -> list[BudgetProgressResponse]:
    progress = await container.get_budget_progress.execute(user_id)
    return [BudgetProgressResponse.from_progress(p) for p in progress]


@router.put("", response_model=BudgetResponse)
async def set_budget(
    body: SetBudgetRequest, container: ContainerDep, user_id: CurrentUserId
) -> BudgetResponse:
    budget = await container.set_budget.execute(
        user_id, body.limit_amount, body.period, category_id=body.category_id
    )
    return BudgetResponse.from_entity(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(budget_id: int, container: ContainerDep, user_id: CurrentUserId) -> Response:
    await container.delete_budget.execute(budget_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
