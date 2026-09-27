import logging

from app.domain.entities.transaction import TransactionType
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository

logger = logging.getLogger(__name__)


class DeleteTransactionUseCase:
    def __init__(
        self,
        transaction_repo: AbstractTransactionRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._tx_repo = transaction_repo
        self._user_repo = user_repo

    async def execute(self, transaction_id: int, user_id: int) -> None:
        tx = await self._tx_repo.get_by_id(transaction_id, user_id, for_update=True)
        if tx is None:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        if tx.transaction_type == TransactionType.SAVINGS:
            raise BusinessRuleViolation("Savings transactions are managed via savings goals")

        await self._tx_repo.delete(transaction_id, user_id)
        await self._user_repo.apply_balance_delta(user_id, tx.account_type, -tx.signed_amount)
        logger.info("Transaction deleted: user=%d id=%d", user_id, transaction_id)
