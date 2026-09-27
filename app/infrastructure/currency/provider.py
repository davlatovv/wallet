import time
from decimal import Decimal

from app.application.interfaces.currency_rate import AbstractUsdRateProvider
from app.domain.exceptions.base import ExternalServiceError
from app.infrastructure.currency.cbu_client import get_usd_rate

_TTL_SECONDS = 600
_cache: tuple[float, Decimal] | None = None  # process-wide: the Container is per-request


class CbuUsdRateProvider(AbstractUsdRateProvider):
    async def get_usd_rate(self) -> Decimal:
        global _cache
        now = time.monotonic()
        if _cache and now - _cache[0] < _TTL_SECONDS:
            return _cache[1]
        try:
            rate = await get_usd_rate()
        except Exception as exc:  # network, JSON, missing USD entry
            if _cache:  # serve a stale rate rather than fail the user's entry
                return _cache[1]
            raise ExternalServiceError("USD rate is temporarily unavailable") from exc
        _cache = (now, rate)
        return rate
