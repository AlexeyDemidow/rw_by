from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from tg_bot.keyboards.keyboards import (
    STATIONS,
    StationCb,
    build_stations_inline,
    station_title,
    build_again_inline,
)
from tg_bot.service.client import ask_backend
from tg_bot.utils.formatters import format_trains, split_message
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


@router.callback_query(F.data == "route:minsk_svetlogorsk")
async def handle_minsk_svetlogorsk(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trip_date = data.get("trip_date")

    if not trip_date:
        await callback.message.answer("⚠️ Сначала выберите дату через /start")
        await callback.answer()
        return

    response = await ask_backend(payload={
        "dep_station": "Минск-Пассажирский",
        "arr_station": "Светлогорск-на-Березине",
        "trip_date": trip_date,
    })

    if not response:
        await callback.message.answer("⚠️ Сервер временно недоступен")
        await callback.answer()
        return

    text = format_trains(response)

    for chunk in split_message(text):
        await callback.message.answer(chunk, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "route:svetlogorsk_minsk")
async def handle_svetlogorsk_minsk(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trip_date = data.get("trip_date")

    if not trip_date:
        await callback.message.answer("⚠️ Сначала выберите дату через /start")
        await callback.answer()
        return

    response = await ask_backend(payload={
        "dep_station": "Светлогорск-на-Березине",
        "arr_station": "Минск-Пассажирский",
        "trip_date": trip_date,
    })

    if not response:
        await callback.message.answer("⚠️ Сервер временно недоступен")
        await callback.answer()
        return

    text = format_trains(response)

    for chunk in split_message(text):
        await callback.message.answer(chunk, parse_mode="HTML")

    await callback.answer()
