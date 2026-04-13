from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.infrastructure.container import Container


class RegisterUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        container: Container | None = data.get("container")
        if user and container:
            await container.ensure_user.execute(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
            )
        return await handler(event, data)
