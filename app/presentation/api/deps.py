from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.infrastructure.container import Container
from app.infrastructure.db.session.factory import async_session_factory
from app.presentation.api.auth.tokens import InvalidToken, decode_token

_bearer = HTTPBearer(auto_error=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """One DB transaction per request (mirrors the bot's DbSessionMiddleware)."""
    async with async_session_factory()() as session:
        async with session.begin():
            yield session


# scope="function": commit before the response is sent, so a client that
# immediately re-reads never sees stale data.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


def get_container(session: SessionDep) -> Container:
    return Container(session)


ContainerDep = Annotated[Container, Depends(get_container)]


async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> int:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        user_id = decode_token(credentials.credentials, settings.jwt_secret)
    except InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from None
    request.state.user_id = user_id  # picked up by RequestLoggingMiddleware
    return user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
