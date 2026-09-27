from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.application.dto.transaction import UpdateTransactionDTO
from app.application.use_cases.transactions.list_transactions import DEFAULT_LIMIT, MAX_LIMIT
from app.domain.entities.transaction import TransactionType
from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.transactions import (
    BudgetAlertResponse,
    CreateTransactionRequest,
    ExpenseCreatedResponse,
    TransactionListResponse,
    TransactionResponse,
    UpdateTransactionRequest,
    UsdRateResponse,
)

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    container: ContainerDep,
    user_id: CurrentUserId,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: str | None = None,
    type: TransactionType | None = None,
    category_id: int | None = None,
    from_dt: Annotated[datetime | None, Query(alias="from")] = None,
    to_dt: Annotated[datetime | None, Query(alias="to")] = None,
) -> TransactionListResponse:
    page = await container.list_transactions.execute(
        user_id, limit=limit, cursor=cursor, transaction_type=type,
        category_id=category_id, from_dt=from_dt, to_dt=to_dt,
    )
    return TransactionListResponse(
        items=[TransactionResponse.from_entity(t) for t in page.items],
        next_cursor=page.next_cursor,
    )


@router.post("/transactions/expense", response_model=ExpenseCreatedResponse,
             status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: CreateTransactionRequest, container: ContainerDep, user_id: CurrentUserId
) -> ExpenseCreatedResponse:
    dto = await container.prepare_transaction.execute(user_id, **body.model_dump())
    result = await container.add_expense.execute(dto)
    return ExpenseCreatedResponse(
        transaction=TransactionResponse.from_entity(result.transaction),
        alerts=[
            BudgetAlertResponse(
                budget_id=a.budget_id, category_name=a.category_name, used_ratio=a.used_ratio,
                limit=a.limit, is_warning=a.is_warning, is_critical=a.is_critical,
            )
            for a in result.alerts
        ],
    )


@router.post("/transactions/income", response_model=TransactionResponse,
             status_code=status.HTTP_201_CREATED)
async def create_income(
    body: CreateTransactionRequest, container: ContainerDep, user_id: CurrentUserId
) -> TransactionResponse:
    dto = await container.prepare_transaction.execute(user_id, **body.model_dump())
    return TransactionResponse.from_entity(await container.add_income.execute(dto))


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    body: UpdateTransactionRequest,
    container: ContainerDep,
    user_id: CurrentUserId,
) -> TransactionResponse:
    dto = UpdateTransactionDTO(
        user_id=user_id, transaction_id=transaction_id, **body.model_dump(exclude_unset=True)
    )
    return TransactionResponse.from_entity(await container.update_transaction.execute(dto))


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int, container: ContainerDep, user_id: CurrentUserId
) -> Response:
    await container.delete_transaction.execute(transaction_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/currency/usd-rate", response_model=UsdRateResponse)
async def usd_rate(container: ContainerDep, _: CurrentUserId) -> UsdRateResponse:
    return UsdRateResponse(rate=await container.usd_rates.get_usd_rate())
