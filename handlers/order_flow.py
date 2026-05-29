from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    game_id = State()
    confirm = State()
    waiting_receipt = State()
