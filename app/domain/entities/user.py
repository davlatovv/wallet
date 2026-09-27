from dataclasses import dataclass
from decimal import Decimal


@dataclass
class UserBalanceEntity:
    user_id: int
    cash_balance: Decimal
    card_balance: Decimal
    currency_balance: Decimal
    total_balance: Decimal
