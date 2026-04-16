from aiogram.fsm.state import State, StatesGroup


class CategoryStates(StatesGroup):
    # Добавление
    adding_name = State()
    adding_icon = State()

    # Редактирование
    editing_name = State()
    editing_icon = State()

    # Подтверждение удаления
    confirming_delete = State()
