from datetime import date

from fastapi import APIRouter, Query, Response

from app.application.use_cases.export.export_transactions import ExportFormat
from app.presentation.api.deps import ContainerDep, CurrentUserId

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/transactions")
async def export_transactions(
    container: ContainerDep,
    user_id: CurrentUserId,
    format: ExportFormat = ExportFormat.XLSX,
    month: date | None = Query(default=None, description="Any day in the target month; defaults to the current month"),
) -> Response:
    result = await container.export_transactions.execute(user_id, format, month)
    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
