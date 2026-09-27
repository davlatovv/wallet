from pydantic import BaseModel, Field

from app.presentation.api.schemas.common import MoneyStr


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(alias="initData", min_length=1)

    model_config = {"populate_by_name": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class BalanceResponse(BaseModel):
    cash_balance: MoneyStr
    card_balance: MoneyStr
    currency_balance: MoneyStr
    total_balance: MoneyStr
    total_income: MoneyStr
    total_expense: MoneyStr
    total_savings: MoneyStr


class MeResponse(BaseModel):
    user_id: int
    timezone: str
    balance: BalanceResponse


class UpdateMeRequest(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
