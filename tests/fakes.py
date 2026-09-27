"""In-memory repository fakes for use-case tests."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from app.application.interfaces.currency_rate import AbstractUsdRateProvider
from app.domain.exceptions.base import ExternalServiceError
from app.domain.entities.budget import BudgetEntity
from app.domain.entities.category import CategoryEntity
from app.domain.entities.debt import DebtEntity, DebtStatus
from app.domain.entities.savings import SavingsGoalEntity, SavingsStatus
from app.domain.entities.transaction import AccountType, TransactionEntity, TransactionType
from app.domain.entities.user import UserBalanceEntity
from app.domain.repositories.abstract_budget import AbstractBudgetRepository
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.domain.repositories.abstract_debt import AbstractDebtRepository
from app.domain.repositories.abstract_savings import AbstractSavingsRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository


class FakeTransactionRepo(AbstractTransactionRepository):
    def __init__(self) -> None:
        self.items: list[TransactionEntity] = []

    async def create(self, user_id, amount, transaction_type, category_id, note,
                     currency="UZS", account_type=AccountType.CARD,
                     original_amount=None, usd_rate=None):
        tx = TransactionEntity(
            id=len(self.items) + 1, user_id=user_id, amount=amount,
            transaction_type=transaction_type, category_id=category_id, note=note,
            created_at=datetime.now(timezone.utc), currency=currency,
            account_type=account_type, original_amount=original_amount, usd_rate=usd_rate,
        )
        self.items.append(tx)
        return tx

    async def get_by_id(self, transaction_id, user_id, for_update=False):
        return next((t for t in self.items if t.id == transaction_id and t.user_id == user_id), None)

    async def list_page(self, user_id, limit, transaction_type=None, category_id=None,
                        from_dt=None, to_dt=None, before=None):
        rows = [t for t in self.items if t.user_id == user_id
                and (transaction_type is None or t.transaction_type == transaction_type)
                and (category_id is None or t.category_id == category_id)
                and (from_dt is None or t.created_at >= from_dt)
                and (to_dt is None or t.created_at <= to_dt)
                and (before is None or (t.created_at, t.id) < before)]
        rows.sort(key=lambda t: (t.created_at, t.id), reverse=True)
        return rows[:limit]

    async def update(self, transaction_id, user_id, changes):
        tx = await self.get_by_id(transaction_id, user_id)
        if tx is None:
            return None
        new = replace(tx, **changes)
        self.items[self.items.index(tx)] = new
        return new

    async def list_by_period(self, user_id, from_dt, to_dt, transaction_type=None):
        return [t for t in self.items if t.user_id == user_id
                and (transaction_type is None or t.transaction_type == transaction_type)]

    async def list_available_months(self, user_id):
        return []

    async def delete(self, transaction_id, user_id):
        tx = await self.get_by_id(transaction_id, user_id)
        if tx:
            self.items.remove(tx)
        return tx is not None

    async def sum_by_period(self, user_id, from_dt, to_dt, transaction_type, category_id=None):
        return sum((t.amount for t in self.items
                    if t.user_id == user_id and t.transaction_type == transaction_type
                    and (category_id is None or t.category_id == category_id)
                    and from_dt <= t.created_at <= to_dt),
                   Decimal("0"))

    async def sum_by_category(self, user_id, from_dt, to_dt, transaction_type):
        return []

    async def sum_balance_by_currency(self, user_id, from_dt, to_dt):
        return []


class FakeUserRepo(AbstractUserRepository):
    def __init__(self) -> None:
        self.balances: dict[int, dict[str, Decimal]] = {}

    def _row(self, user_id: int) -> dict[str, Decimal]:
        return self.balances.setdefault(
            user_id, {"cash": Decimal("0"), "card": Decimal("0"), "currency": Decimal("0")}
        )

    def __init_tz(self):
        if not hasattr(self, "timezones"):
            self.timezones = {}

    async def get_or_create(self, telegram_id, username, first_name):
        self.__init_tz()
        created = telegram_id not in self.balances
        self._row(telegram_id)
        self.timezones.setdefault(telegram_id, "UTC")
        return created

    async def get_timezone(self, user_id):
        self.__init_tz()
        return self.timezones.get(user_id)

    async def update_timezone(self, user_id, timezone):
        self.__init_tz()
        if user_id not in self.balances:
            return None
        self.timezones[user_id] = timezone
        return timezone

    async def exists(self, telegram_id):
        return telegram_id in self.balances

    async def get_balance(self, user_id):
        if user_id not in self.balances:
            return None
        r = self.balances[user_id]
        return UserBalanceEntity(user_id, r["cash"], r["card"], r["currency"],
                                 r["cash"] + r["card"] + r["currency"])

    async def apply_balance_delta(self, user_id, account_type, amount_delta):
        self._row(user_id)[account_type.value] += amount_delta
        return await self.get_balance(user_id)


class FakeBudgetRepo(AbstractBudgetRepository):
    def __init__(self, budgets: list[BudgetEntity] | None = None) -> None:
        self.budgets = budgets or []

    async def create(self, user_id, category_id, limit_amount, period, start_date):
        b = BudgetEntity(len(self.budgets) + 1, user_id, category_id, limit_amount, period, start_date)
        self.budgets.append(b)
        return b

    async def get_by_id(self, budget_id, user_id):
        return next((b for b in self.budgets if b.id == budget_id and b.user_id == user_id), None)

    async def list_by_user(self, user_id):
        return [b for b in self.budgets if b.user_id == user_id]

    async def update_limit(self, budget_id, user_id, limit_amount):
        b = await self.get_by_id(budget_id, user_id)
        if b is None:
            return None
        new = replace(b, limit_amount=limit_amount)
        self.budgets[self.budgets.index(b)] = new
        return new

    async def delete(self, budget_id, user_id):
        b = await self.get_by_id(budget_id, user_id)
        if b:
            self.budgets.remove(b)
        return b is not None


class FakeCategoryRepo(AbstractCategoryRepository):
    def __init__(self, owned: dict[int, int] | None = None) -> None:
        """owned: category_id -> user_id"""
        self.owned = owned or {}

    async def get_by_id(self, category_id, user_id):
        if self.owned.get(category_id) != user_id:
            return None
        return CategoryEntity(category_id, user_id, "cat", None, None, False, "both")

    async def create(self, *a, **k): raise NotImplementedError
    async def list_by_user(self, *a, **k): raise NotImplementedError
    async def list_root(self, *a, **k): raise NotImplementedError
    async def list_children(self, *a, **k): raise NotImplementedError
    async def update(self, *a, **k): raise NotImplementedError
    async def delete(self, *a, **k): raise NotImplementedError
    async def seed_defaults(self, *a, **k): raise NotImplementedError


class FakeRateProvider(AbstractUsdRateProvider):
    def __init__(self, rate: str = "12500", fail: bool = False) -> None:
        self.rate, self.fail, self.calls = Decimal(rate), fail, 0

    async def get_usd_rate(self):
        self.calls += 1
        if self.fail:
            raise ExternalServiceError("down")
        return self.rate


class MemCategoryRepo(AbstractCategoryRepository):
    """Fully functional in-memory category store."""

    def __init__(self) -> None:
        self.rows: dict[int, CategoryEntity] = {}
        self._next = 1

    def add(self, user_id, name="c", *, system=False, parent_id=None, ctype="expense") -> CategoryEntity:
        c = CategoryEntity(self._next, user_id, name, None, parent_id, system, ctype)
        self.rows[c.id] = c
        self._next += 1
        return c

    async def create(self, user_id, name, icon, parent_id, category_type):
        c = self.add(user_id, name, parent_id=parent_id, ctype=category_type)
        c.icon = icon
        return c

    async def get_by_id(self, category_id, user_id):
        c = self.rows.get(category_id)
        return c if c and c.user_id == user_id else None

    async def list_by_user(self, user_id, category_type=None):
        return [c for c in self.rows.values() if c.user_id == user_id
                and (category_type is None or c.category_type in (category_type, "both"))]

    async def list_root(self, user_id, category_type=None):
        return [c for c in await self.list_by_user(user_id, category_type) if c.parent_id is None]

    async def list_children(self, user_id, parent_id):
        return [c for c in await self.list_by_user(user_id) if c.parent_id == parent_id]

    async def update(self, category_id, user_id, name, icon):
        c = await self.get_by_id(category_id, user_id)
        if c:
            c.name, c.icon = name, icon
        return c

    async def delete(self, category_id, user_id):
        return self.rows.pop(category_id, None) is not None if await self.get_by_id(category_id, user_id) else False

    async def seed_defaults(self, user_id):
        pass


class MemDebtRepo(AbstractDebtRepository):
    def __init__(self) -> None:
        self.rows: dict[int, DebtEntity] = {}

    async def create(self, user_id, counterparty, amount, debt_type, description, due_date):
        d = DebtEntity(len(self.rows) + 1, user_id, counterparty, amount, debt_type,
                       DebtStatus.ACTIVE, description, due_date, datetime.now(timezone.utc))
        self.rows[d.id] = d
        return d

    async def get_by_id(self, debt_id, user_id):
        d = self.rows.get(debt_id)
        return d if d and d.user_id == user_id else None

    async def list_by_user(self, user_id, status=None):
        return [d for d in self.rows.values()
                if d.user_id == user_id and (status is None or d.status == status)]

    async def settle(self, debt_id, user_id):
        d = await self.get_by_id(debt_id, user_id)
        if d:
            d.status = DebtStatus.SETTLED
        return d

    async def delete(self, debt_id, user_id):
        return bool(await self.get_by_id(debt_id, user_id)) and self.rows.pop(debt_id) is not None


class MemSavingsRepo(AbstractSavingsRepository):
    def __init__(self) -> None:
        self.rows: dict[int, SavingsGoalEntity] = {}

    async def create(self, user_id, name, target_amount, description, deadline):
        g = SavingsGoalEntity(len(self.rows) + 1, user_id, name, target_amount, Decimal("0"),
                              description, deadline, SavingsStatus.ACTIVE, datetime.now(timezone.utc))
        self.rows[g.id] = g
        return g

    async def get_by_id(self, goal_id, user_id):
        g = self.rows.get(goal_id)
        return g if g and g.user_id == user_id else None

    async def list_by_user(self, user_id, status=None):
        return [g for g in self.rows.values()
                if g.user_id == user_id and (status is None or g.status == status)]

    async def add_funds(self, goal_id, user_id, amount):
        g = await self.get_by_id(goal_id, user_id)
        if g:
            g.current_amount += amount
            if g.is_completed and g.status == SavingsStatus.ACTIVE:
                g.status = SavingsStatus.COMPLETED
        return g

    async def mark_completed(self, goal_id, user_id):
        g = await self.get_by_id(goal_id, user_id)
        if g:
            g.status = SavingsStatus.COMPLETED
        return g

    async def delete(self, goal_id, user_id):
        return bool(await self.get_by_id(goal_id, user_id)) and self.rows.pop(goal_id) is not None
