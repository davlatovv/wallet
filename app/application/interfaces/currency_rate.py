from abc import ABC, abstractmethod
from decimal import Decimal


class AbstractUsdRateProvider(ABC):
    @abstractmethod
    async def get_usd_rate(self) -> Decimal:
        """UZS per 1 USD. Raises ExternalServiceError if unavailable."""
