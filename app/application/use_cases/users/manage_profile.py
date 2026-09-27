import logging

import pytz

from app.domain.exceptions.base import NotFoundError, ValidationError
from app.domain.repositories.abstract_user import AbstractUserRepository

logger = logging.getLogger(__name__)


class GetUserTimezoneUseCase:
    def __init__(self, repo: AbstractUserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int) -> str:
        tz = await self._repo.get_timezone(user_id)
        return tz or "UTC"


class UpdateUserTimezoneUseCase:
    def __init__(self, repo: AbstractUserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, timezone: str) -> str:
        if timezone not in pytz.all_timezones_set:
            raise ValidationError(f"Unknown timezone: {timezone}")
        updated = await self._repo.update_timezone(user_id, timezone)
        if updated is None:
            raise NotFoundError(f"User {user_id} not found")
        logger.info("Timezone updated: user=%d timezone=%s", user_id, timezone)
        return updated
