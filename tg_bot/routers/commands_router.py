from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from tg_bot.keyboards.keyboards import mode_keyboard
from tg_bot.service.client import ask_backend
from tg_bot.utils.states import BotStates

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    today = datetime.now()
    max_date = today + timedelta(days=30)

    calendar = SimpleCalendar(show_alerts=True)
    # Задаем диапазон дат внутри календаря
    calendar.set_dates_range(today, max_date)

    await message.answer(
        f"Привет! Выберите дату (доступно с {today.strftime('%d.%m.%Y')} по {max_date.strftime('%d.%m.%Y')}):",
        reply_markup=await calendar.start_calendar()
    )
    await state.set_state(BotStates.start)


@router.callback_query(SimpleCalendarCallback.filter())
async def process_calendar_selection(
        callback: CallbackQuery,
        callback_data: SimpleCalendarCallback,
        state: FSMContext
):
    # Повторяем те же ограничения при обработке клика, чтобы календарь корректно отображал фильтр
    today = datetime.now()
    max_date = today + timedelta(days=30)

    calendar = SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(today, max_date)

    # Обрабатываем выбор пользователя
    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        # сохраняем выбранную дату в FSM
        await state.update_data(trip_date=date.strftime('%Y-%m-%d'))

        await callback.message.edit_text(
            f"✅ Вы успешно выбрали дату: {date.strftime('%d.%m.%Y')}\nТеперь выберите маршрут:",
            reply_markup=build_routes_inline(),
        )

        await callback.answer()


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
