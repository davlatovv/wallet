import logging

from app.application.dto.transaction import AddTransactionDTO
from app.domain.entities.transaction import TransactionEntity, TransactionType
from app.domain.exceptions.base import NotFoundError
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository

logger = logging.getLogger(__name__)


class AddIncomeUseCase:
    def __init__(
        self,
        transaction_repo: AbstractTransactionRepository,
        user_repo: AbstractUserRepository,
        category_repo: AbstractCategoryRepository | None = None,
    ) -> None:
        self._tx_repo = transaction_repo
        self._user_repo = user_repo
        self._cat_repo = category_repo

    async def execute(self, dto: AddTransactionDTO) -> TransactionEntity:
        if dto.category_id is not None and self._cat_repo is not None:
            if await self._cat_repo.get_by_id(dto.category_id, dto.user_id) is None:
                raise NotFoundError(f"Category {dto.category_id} not found")
        transaction = await self._tx_repo.create(
            user_id=dto.user_id,
            amount=dto.amount,
            transaction_type=TransactionType.INCOME,
            category_id=dto.category_id,
            note=dto.note,
            currency=dto.currency,
            account_type=dto.account_type,
            original_amount=dto.original_amount,
            usd_rate=dto.usd_rate,
        )
        await self._user_repo.apply_balance_delta(dto.user_id, dto.account_type, dto.amount)
        logger.info("Income created: user=%d amount=%s", dto.user_id, dto.amount)
        return transaction
