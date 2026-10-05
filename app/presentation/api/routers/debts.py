from fastapi import APIRouter, Response, status

from app.domain.entities.debt import DebtStatus
from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.debts import CreateDebtRequest, DebtResponse

router = APIRouter(prefix="/debts", tags=["debts"])


@router.get("", response_model=list[DebtResponse])
async def list_debts(
    container: ContainerDep, user_id: CurrentUserId, status: DebtStatus | None = None
) -> list[DebtResponse]:
    debts = await container.list_debts.execute(user_id, status)
    return [DebtResponse.from_entity(d) for d in debts]


@router.post("", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
async def create_debt(
    body: CreateDebtRequest, container: ContainerDep, user_id: CurrentUserId
) -> DebtResponse:
    debt = await container.add_debt.execute(
        user_id, body.counterparty, body.amount, body.debt_type, body.description, body.due_date
    )
    return DebtResponse.from_entity(debt)


@router.post("/{debt_id}/settle", response_model=DebtResponse)
async def settle_debt(debt_id: int, container: ContainerDep, user_id: CurrentUserId) -> DebtResponse:
    return DebtResponse.from_entity(await container.settle_debt.execute(debt_id, user_id))


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt(debt_id: int, container: ContainerDep, user_id: CurrentUserId) -> Response:
    await container.delete_debt.execute(debt_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
