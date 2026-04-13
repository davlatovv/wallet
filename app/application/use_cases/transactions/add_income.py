import logging

from app.application.dto.transaction import AddTransactionDTO
from app.domain.entities.transaction import TransactionEntity, TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository

logger = logging.getLogger(__name__)


class AddIncomeUseCase:
    def __init__(self, transaction_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = transaction_repo

    async def execute(self, dto: AddTransactionDTO) -> TransactionEntity:
        transaction = await self._tx_repo.create(
            user_id=dto.user_id,
            amount=dto.amount,
            transaction_type=TransactionType.INCOME,
            category_id=dto.category_id,
            note=dto.note,
        )
        logger.info("Income created: user=%d amount=%s", dto.user_id, dto.amount)
        return transaction
