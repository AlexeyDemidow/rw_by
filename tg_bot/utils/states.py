from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    start = State()
    searching = State()
