import pytest

from app.application.use_cases.categories.manage_categories import (
    CreateCategoryUseCase, DeleteCategoryUseCase, ListAllCategoriesUseCase, RenameCategoryUseCase,
)
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError, ValidationError
from tests.fakes import MemCategoryRepo

U, OTHER = 1, 2


@pytest.fixture
def repo():
    return MemCategoryRepo()


async def test_create_trims_and_stores(repo):
    c = await CreateCategoryUseCase(repo).execute(U, "  Coffee  ", " ☕ ", None, "expense")
    assert (c.name, c.icon, c.is_system) == ("Coffee", "☕", False)


@pytest.mark.parametrize("name", ["", "   ", "x" * 65])
async def test_create_rejects_bad_name(repo, name):
    with pytest.raises(ValidationError):
        await CreateCategoryUseCase(repo).execute(U, name)


async def test_create_rejects_bad_type_and_long_icon(repo):
    uc = CreateCategoryUseCase(repo)
    with pytest.raises(ValidationError):
        await uc.execute(U, "a", category_type="weird")
    with pytest.raises(ValidationError):
        await uc.execute(U, "a", icon="123456789")


async def test_parent_must_be_own_and_root(repo):
    mine = repo.add(U, "root")
    child = repo.add(U, "child", parent_id=mine.id)
    foreign = repo.add(OTHER, "theirs")
    uc = CreateCategoryUseCase(repo)
    assert (await uc.execute(U, "ok", parent_id=mine.id)).parent_id == mine.id
    with pytest.raises(NotFoundError):
        await uc.execute(U, "x", parent_id=foreign.id)
    with pytest.raises(BusinessRuleViolation):
        await uc.execute(U, "grandchild", parent_id=child.id)


async def test_system_categories_are_protected(repo):
    sys_cat = repo.add(U, "Food", system=True)
    with pytest.raises(BusinessRuleViolation):
        await DeleteCategoryUseCase(repo).execute(sys_cat.id, U)
    with pytest.raises(BusinessRuleViolation):
        await RenameCategoryUseCase(repo).execute(sys_cat.id, U, "New", None)
    assert repo.rows[sys_cat.id].name == "Food"


async def test_rename_and_delete_custom(repo):
    c = repo.add(U, "old")
    out = await RenameCategoryUseCase(repo).execute(c.id, U, " new ", None)
    assert out.name == "new"
    await DeleteCategoryUseCase(repo).execute(c.id, U)
    assert c.id not in repo.rows


async def test_other_users_category_is_not_found(repo):
    c = repo.add(OTHER, "theirs")
    with pytest.raises(NotFoundError):
        await DeleteCategoryUseCase(repo).execute(c.id, U)
    with pytest.raises(NotFoundError):
        await RenameCategoryUseCase(repo).execute(c.id, U, "x", None)
    assert c.id in repo.rows and c.name == "theirs"


async def test_list_all_includes_children_and_filters_type(repo):
    root = repo.add(U, "r", ctype="income")
    repo.add(U, "kid", parent_id=root.id, ctype="income")
    repo.add(U, "exp", ctype="expense")
    repo.add(U, "both", ctype="both")
    repo.add(OTHER, "foreign")
    uc = ListAllCategoriesUseCase(repo)
    assert len(await uc.execute(U)) == 4
    assert {c.name for c in await uc.execute(U, "income")} == {"r", "kid", "both"}
