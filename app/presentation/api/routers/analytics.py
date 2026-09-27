from fastapi import APIRouter

from app.application.use_cases.analytics.get_report import ReportPeriod
from app.presentation.api.deps import ContainerDep, CurrentUserId
from app.presentation.api.schemas.analytics import MonthResponse, ReportResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/report", response_model=ReportResponse)
async def report(
    container: ContainerDep, user_id: CurrentUserId, period: ReportPeriod = ReportPeriod.MONTH
) -> ReportResponse:
    tz = await container.get_user_timezone.execute(user_id)
    return ReportResponse.from_result(await container.get_report.execute(user_id, period, tz))


@router.get("/months", response_model=list[MonthResponse])
async def months(container: ContainerDep, user_id: CurrentUserId) -> list[MonthResponse]:
    pairs = await container.list_report_months.execute(user_id)
    return [MonthResponse(year=y, month=m) for y, m in pairs]
