from aiogram.fsm.state import State, StatesGroup


class ExpenseStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()
    waiting_for_currency = State()
    waiting_for_note = State()
    confirming = State()
