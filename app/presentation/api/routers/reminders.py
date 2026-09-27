from fastapi import APIRouter, Response, status

from app.application.dto.reminder import (
    CreateCreditReminderDTO, CreateEducationReminderDTO,
    CreateInstallmentReminderDTO, CreateRegularReminderDTO,
)
from app.domain.entities.reminder import ReminderStatus
from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.reminders import (
    CreateCreditRequest, CreateEducationRequest, CreateInstallmentRequest, CreateRegularRequest,
    CreditPreviewRequest, CreditPreviewResponse, RecordPaymentRequest, ReminderResponse,
)

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    container: ContainerDep, user_id: CurrentUserId, status: ReminderStatus | None = None
) -> list[ReminderResponse]:
    """Soonest payment first. Schedules are only included by the detail endpoint."""
    items = await container.list_reminders.execute(user_id)
    return [ReminderResponse.from_dto(r) for r in items if status is None or r.status == status]


@router.post("/credit/preview", response_model=CreditPreviewResponse)
async def preview_credit(body: CreditPreviewRequest, container: ContainerDep,
                         _: CurrentUserId) -> CreditPreviewResponse:
    preview = container.preview_credit.execute(
        body.total_amount, body.interest_rate, body.months_total, body.payment_type
    )
    return CreditPreviewResponse.from_preview(preview)


@router.post("/credit", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_credit(body: CreateCreditRequest, container: ContainerDep,
                        user_id: CurrentUserId) -> ReminderResponse:
    dto = CreateCreditReminderDTO(
        **body.model_dump(), payment_day=body.first_payment_date.day
    )
    return ReminderResponse.from_dto(await container.create_credit_reminder.execute(user_id, dto))


@router.post("/installment", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_installment(body: CreateInstallmentRequest, container: ContainerDep,
                             user_id: CurrentUserId) -> ReminderResponse:
    dto = CreateInstallmentReminderDTO(**body.model_dump(), payment_day=body.first_payment_date.day)
    return ReminderResponse.from_dto(
        await container.create_installment_reminder.execute(user_id, dto))


@router.post("/education", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_education(body: CreateEducationRequest, container: ContainerDep,
                           user_id: CurrentUserId) -> ReminderResponse:
    dto = CreateEducationReminderDTO(**body.model_dump(), payment_day=body.first_payment_date.day)
    return ReminderResponse.from_dto(
        await container.create_education_reminder.execute(user_id, dto))


@router.post("/regular", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_regular(body: CreateRegularRequest, container: ContainerDep,
                         user_id: CurrentUserId) -> ReminderResponse:
    dto = CreateRegularReminderDTO(**body.model_dump(), payment_day=body.first_payment_date.day)
    return ReminderResponse.from_dto(await container.create_regular_reminder.execute(user_id, dto))


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(reminder_id: int, container: ContainerDep,
                       user_id: CurrentUserId) -> ReminderResponse:
    return ReminderResponse.from_dto(
        await container.get_reminder_detail.execute(reminder_id, user_id))


@router.post("/{reminder_id}/payments", response_model=ReminderResponse)
async def record_payment(reminder_id: int, container: ContainerDep, user_id: CurrentUserId,
                         body: RecordPaymentRequest | None = None) -> ReminderResponse:
    """Marks the current instalment as paid and moves to the next month.
    Does not create an expense transaction (same as the bot)."""
    dto = await container.record_payment.execute(
        reminder_id, user_id, body.amount if body else None)
    return ReminderResponse.from_dto(dto)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(reminder_id: int, container: ContainerDep,
                          user_id: CurrentUserId) -> Response:
    await container.delete_reminder.execute(reminder_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
