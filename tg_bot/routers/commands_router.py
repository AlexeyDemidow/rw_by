from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tg_bot.keyboards.keyboards import mode_keyboard
from tg_bot.service.client import ask_backend
from tg_bot.utils.states import BotStates

router = Router()

from aiogram import F


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("👋 Добро пожаловать!", reply_markup=mode_keyboard)
    await state.set_state(BotStates.start)


@router.message(F.text == "Минск-Светлогорск 21.10.2026", BotStates.start)
async def handle_schedule_text(message: Message, state: FSMContext):
    response = await ask_backend(
        payload={
            'dep_station': 'Минск-Пассажирский',
            'arr_station': 'Светлогорск-на-Березине',
            'trip_date': '2026-10-21',
        }
    )

    if response:
        await message.answer(str(response))
    else:
        await message.answer("⚠️ Сервер временно недоступен")


@router.message(F.text == "Светлогорск-Минск 25.10.2026", BotStates.start)
async def handle_schedule_text_another(message: Message, state: FSMContext):

    response = await ask_backend(
        payload={
            'dep_station': 'Светлогорск-на-Березине',
            'arr_station': 'Минск-Пассажирский',
            'trip_date': '2026-10-25',
        }
    )
    if response:
        await message.answer(str(response))
    else:
        await message.answer("⚠️ Сервер временно недоступен")
