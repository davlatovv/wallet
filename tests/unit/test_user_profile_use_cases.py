import pytest

from app.application.use_cases.users.manage_profile import (
    GetUserTimezoneUseCase, UpdateUserTimezoneUseCase,
)
from app.domain.exceptions.base import NotFoundError, ValidationError
from tests.fakes import FakeUserRepo


async def test_new_user_defaults_to_utc():
    repo = FakeUserRepo()
    await repo.get_or_create(1, None, None)
    assert await GetUserTimezoneUseCase(repo).execute(1) == "UTC"


async def test_update_and_read_back():
    repo = FakeUserRepo()
    await repo.get_or_create(1, None, None)
    out = await UpdateUserTimezoneUseCase(repo).execute(1, "Asia/Tashkent")
    assert out == "Asia/Tashkent"
    assert await GetUserTimezoneUseCase(repo).execute(1) == "Asia/Tashkent"


async def test_unknown_timezone_rejected():
    repo = FakeUserRepo()
    await repo.get_or_create(1, None, None)
    with pytest.raises(ValidationError):
        await UpdateUserTimezoneUseCase(repo).execute(1, "Mars/Phobos")


async def test_unknown_user_is_not_found():
    with pytest.raises(NotFoundError):
        await UpdateUserTimezoneUseCase(FakeUserRepo()).execute(999, "UTC")
