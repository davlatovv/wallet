from aiogram.fsm.state import State, StatesGroup


class SavingsStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_target = State()
    waiting_for_deadline = State()
    confirming = State()
    # Fund flow
    waiting_for_fund_amount = State()
