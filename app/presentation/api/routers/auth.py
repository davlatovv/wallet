from fastapi import APIRouter, HTTPException, status

from app.config.settings import settings
from app.presentation.api.auth.telegram import InvalidInitData, validate_init_data
from app.presentation.api.auth.tokens import issue_token
from app.presentation.api.deps import ContainerDep
from app.presentation.api.schemas.auth import TelegramAuthRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=TokenResponse)
async def login_with_telegram(body: TelegramAuthRequest, container: ContainerDep) -> TokenResponse:
    try:
        tg_user = validate_init_data(
            body.init_data, settings.bot_token, settings.init_data_max_age_seconds
        )
    except InvalidInitData as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid initData: {exc}") from None

    await container.ensure_user.execute(
        telegram_id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name
    )
    token, expires_in = issue_token(tg_user.id, settings.jwt_secret, settings.jwt_ttl_minutes)
    return TokenResponse(access_token=token, expires_in=expires_in)
