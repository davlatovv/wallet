from aiogram.fsm.state import State, StatesGroup


class ReminderStates(StatesGroup):
    # Выбор типа
    choosing_type = State()

    # Общее
    waiting_for_name = State()
    waiting_for_payment_day = State()
    waiting_for_first_date = State()

    # Кредит
    credit_total = State()
    credit_rate = State()
    credit_months = State()
    credit_payment_type = State()
    credit_confirming = State()

    # Рассрочка
    inst_total = State()
    inst_monthly = State()
    inst_months = State()
    inst_confirming = State()

    # Учёба / Постоянный (общий flow)
    edu_total = State()       # для учёбы (total_amount)
    edu_payment = State()     # сумма платежа
    edu_confirming = State()
