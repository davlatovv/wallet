from fastapi import APIRouter

from app.infrastructure.container import Container
from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.auth import BalanceResponse, MeResponse, UpdateMeRequest

router = APIRouter(tags=["me"])


async def _balance(container: Container, user_id: int) -> BalanceResponse:
    result = await container.get_balance.execute(user_id)
    return BalanceResponse(
        cash_balance=result.cash_balance,
        card_balance=result.card_balance,
        currency_balance=result.currency_balance,
        total_balance=result.total_balance,
        total_income=result.total_income,
        total_expense=result.total_expense,
        total_savings=result.total_savings,
    )


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(container: ContainerDep, user_id: CurrentUserId) -> BalanceResponse:
    return await _balance(container, user_id)


@router.get("/me", response_model=MeResponse)
async def get_me(container: ContainerDep, user_id: CurrentUserId) -> MeResponse:
    tz = await container.get_user_timezone.execute(user_id)
    return MeResponse(user_id=user_id, timezone=tz, balance=await _balance(container, user_id))


@router.patch("/me", response_model=MeResponse)
async def update_me(
    body: UpdateMeRequest, container: ContainerDep, user_id: CurrentUserId
) -> MeResponse:
    tz = await container.update_user_timezone.execute(user_id, body.timezone)
    return MeResponse(user_id=user_id, timezone=tz, balance=await _balance(container, user_id))
