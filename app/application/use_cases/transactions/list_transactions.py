import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.entities.transaction import TransactionEntity, TransactionType
from app.domain.exceptions.base import ValidationError
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository

DEFAULT_LIMIT = 30
MAX_LIMIT = 100


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def encode_cursor(created_at: datetime, transaction_id: int) -> str:
    raw = f"{created_at.isoformat()}|{transaction_id}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        created, tx_id = base64.urlsafe_b64decode(cursor.encode()).decode().rsplit("|", 1)
        return _aware(datetime.fromisoformat(created)), int(tx_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise ValidationError("Invalid cursor") from None


@dataclass
class TransactionPage:
    items: list[TransactionEntity]
    next_cursor: str | None


class ListTransactionsUseCase:
    def __init__(self, transaction_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = transaction_repo

    async def execute(
        self,
        user_id: int,
        limit: int = DEFAULT_LIMIT,
        cursor: str | None = None,
        transaction_type: TransactionType | None = None,
        category_id: int | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> TransactionPage:
        if not 1 <= limit <= MAX_LIMIT:
            raise ValidationError(f"limit must be between 1 and {MAX_LIMIT}")
        rows = await self._tx_repo.list_page(
            user_id=user_id,
            limit=limit + 1,  # one extra row tells us whether another page exists
            transaction_type=transaction_type,
            category_id=category_id,
            from_dt=_aware(from_dt),
            to_dt=_aware(to_dt),
            before=decode_cursor(cursor) if cursor else None,
        )
        items = rows[:limit]
        next_cursor = None
        if len(rows) > limit:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        return TransactionPage(items=items, next_cursor=next_cursor)
