import logging

from decimal import Decimal

from app.application.dto.transaction import UpdateTransactionDTO
from app.application.interfaces.currency_rate import AbstractUsdRateProvider
from app.application.use_cases.transactions.prepare_transaction import usd_to_uzs
from app.domain.entities.transaction import AccountType, TransactionEntity, TransactionType
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError, ValidationError
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository

logger = logging.getLogger(__name__)

_EDITABLE = {
    "amount", "category_id", "note", "currency", "account_type",
    "original_amount", "usd_rate", "created_at",
}


class UpdateTransactionUseCase:
    def __init__(
        self,
        transaction_repo: AbstractTransactionRepository,
        category_repo: AbstractCategoryRepository,
        user_repo: AbstractUserRepository,
        rate_provider: AbstractUsdRateProvider,
    ) -> None:
        self._rates = rate_provider
        self._tx_repo = transaction_repo
        self._cat_repo = category_repo
        self._user_repo = user_repo

    async def execute(self, dto: UpdateTransactionDTO) -> TransactionEntity:
        old = await self._tx_repo.get_by_id(dto.transaction_id, dto.user_id, for_update=True)
        if old is None:
            raise NotFoundError(f"Transaction {dto.transaction_id} not found")
        if old.transaction_type == TransactionType.SAVINGS:
            raise BusinessRuleViolation("Savings transactions are managed via savings goals")

        changes = await self._build_changes(dto, old)
        for required in ("amount", "currency", "created_at"):
            if required in changes and changes[required] is None:
                raise ValidationError(f"{required} cannot be null")

        category_id = changes.get("category_id")
        if category_id is not None and await self._cat_repo.get_by_id(category_id, dto.user_id) is None:
            raise NotFoundError(f"Category {category_id} not found")

        if not changes:
            return old
        updated = await self._tx_repo.update(dto.transaction_id, dto.user_id, changes)
        if updated is None:  # deleted between lock and update; cannot happen under FOR UPDATE
            raise NotFoundError(f"Transaction {dto.transaction_id} not found")

        if old.amount != updated.amount or old.account_type != updated.account_type:
            await self._user_repo.apply_balance_delta(dto.user_id, old.account_type, -old.signed_amount)
            await self._user_repo.apply_balance_delta(dto.user_id, updated.account_type, updated.signed_amount)
        logger.info("Transaction updated: user=%d id=%d fields=%s",
                    dto.user_id, dto.transaction_id, sorted(changes))
        return updated

    async def _build_changes(self, dto: UpdateTransactionDTO, old: TransactionEntity) -> dict:
        changes = {k: getattr(dto, k) for k in dto.model_fields_set & _EDITABLE}
        for required in ("amount", "currency", "created_at"):
            if required in changes and changes[required] is None:
                raise ValidationError(f"{required} cannot be null")

        currency = changes.get("currency", old.currency)
        currency_changed = currency != old.currency
        if currency_changed and "account_type" not in changes:
            changes["account_type"] = AccountType.from_currency(currency)
        if changes.get("account_type") is None:
            changes.pop("account_type", None)

        if currency == "USD":
            if "amount" in changes:
                entered = changes["amount"].quantize(Decimal("0.01"))
                # keep the historical rate when only the amount of a USD entry is edited
                rate = old.usd_rate if (not currency_changed and old.usd_rate) else await self._rates.get_usd_rate()
                changes.update(
                    amount=usd_to_uzs(entered, rate), original_amount=entered, usd_rate=rate)
            elif currency_changed:
                raise ValidationError("amount is required when switching to USD")
        elif currency_changed:
            changes["original_amount"] = None
            changes["usd_rate"] = None
        return changes
