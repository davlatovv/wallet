from aiogram.fsm.state import State, StatesGroup


class InstallmentStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_total = State()
    waiting_for_monthly = State()
    waiting_for_months = State()
    waiting_for_first_payment = State()
    confirming = State()
