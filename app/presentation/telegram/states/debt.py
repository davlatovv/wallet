from aiogram.fsm.state import State, StatesGroup


class DebtStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_counterparty = State()
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_due_date = State()
    confirming = State()
