from fastapi import APIRouter, status

from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.savings import (
    CreateSavingsGoalRequest, DepositRequest, SavingsGoalResponse,
)

router = APIRouter(prefix="/savings", tags=["savings"])


@router.get("", response_model=list[SavingsGoalResponse])
async def list_goals(
    container: ContainerDep, user_id: CurrentUserId, active_only: bool = False
) -> list[SavingsGoalResponse]:
    goals = await container.list_savings.execute(user_id, active_only)
    return [SavingsGoalResponse.from_entity(g) for g in goals]


@router.post("", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    body: CreateSavingsGoalRequest, container: ContainerDep, user_id: CurrentUserId
) -> SavingsGoalResponse:
    goal = await container.create_savings_goal.execute(
        user_id, body.name, body.target_amount, body.description, body.deadline
    )
    return SavingsGoalResponse.from_entity(goal)


@router.post("/{goal_id}/deposit", response_model=SavingsGoalResponse)
async def deposit(
    goal_id: int, body: DepositRequest, container: ContainerDep, user_id: CurrentUserId
) -> SavingsGoalResponse:
    goal = await container.add_to_savings.execute(goal_id, user_id, body.amount)
    return SavingsGoalResponse.from_entity(goal)
