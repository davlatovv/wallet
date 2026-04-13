from aiogram.fsm.state import State, StatesGroup


class BudgetStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_limit = State()
    waiting_for_period = State()
    confirming = State()
