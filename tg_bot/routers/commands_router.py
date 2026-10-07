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


def _calendar() -> SimpleCalendar:
    today = datetime.now()
    calendar = SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(today, today + timedelta(days=30))
    return calendar


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    today = datetime.now()
    max_date = today + timedelta(days=30)

    await state.clear()
    await message.answer(
        f"Привет! Выберите дату (доступно с {today.strftime('%d.%m.%Y')} по {max_date.strftime('%d.%m.%Y')}):",
        reply_markup=await _calendar().start_calendar(),
    )
    await state.set_state(BotStates.start)


@router.callback_query(SimpleCalendarCallback.filter())
async def process_calendar_selection(
    callback: CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext
):
    selected, date = await _calendar().process_selection(callback, callback_data)

    if selected:
        await state.update_data(trip_date=date.strftime("%Y-%m-%d"))

        await callback.message.edit_text(
            f"✅ Дата: {date.strftime('%d.%m.%Y')}\nВыберите станцию отправления:",
            reply_markup=build_stations_inline(step="from"),
        )
        await callback.answer()


@router.callback_query(StationCb.filter(F.action == "no_action"))
async def on_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(StationCb.filter(F.action == "page"))
async def on_page(callback: CallbackQuery, callback_data: StationCb):
    await callback.message.edit_reply_markup(
        reply_markup=build_stations_inline(callback_data.step, callback_data.value, callback_data.src)
    )
    await callback.answer()


@router.callback_query(StationCb.filter(F.action == "pick"))
async def on_pick(callback: CallbackQuery, callback_data: StationCb, state: FSMContext):
    data = await state.get_data()
    trip_date = data.get("trip_date")

    # состояние могло сброситься (перезапуск бота, повторный /start)
    if not trip_date:
        await callback.message.answer("⚠️ Сначала выберите дату через /start")
        await callback.answer()
        return

    # выбор отправления
    if callback_data.step == "from":
        await callback.message.edit_text(
            f"Отправление: <b>{station_title(callback_data.value)}</b>\nВыберите станцию прибытия:",
            reply_markup=build_stations_inline(step="to", page=0, src=callback_data.value),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # выбор станции прибытия
    dep = STATIONS[callback_data.src]
    arr = STATIONS[callback_data.value]

    await callback.message.edit_text(
        f"Маршрут: <b>{station_title(callback_data.src)} → {station_title(callback_data.value)}</b>\n"
        f"Дата: {datetime.strptime(trip_date, '%Y-%m-%d').strftime('%d.%m.%Y')}",
        parse_mode="HTML",
    )

    response = await ask_backend(payload={
        "dep_station": dep,
        "arr_station": arr,
        "trip_date": trip_date,
    })

    if not response:
        await callback.message.answer("⚠️ Сервер временно недоступен")
        await callback.answer()
        return

    chunks = split_message(format_trains(response))
    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        await callback.message.answer(
            chunk,
            parse_mode="HTML",
            reply_markup=build_again_inline() if is_last else None,
        )

    await callback.answer()


@router.callback_query(F.data == "again:route")
async def on_again_route(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trip_date = data.get("trip_date")

    if not trip_date:
        await callback.message.answer("⚠️ Сначала выберите дату через /start")
        await callback.answer()
        return

    # убираем кнопки у старого сообщения, чтобы не плодить дубли
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"Дата: {datetime.strptime(trip_date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n"
        "Выберите станцию отправления:",
        reply_markup=build_stations_inline(step="from"),
    )
    await callback.answer()


@router.callback_query(F.data == "again:date")
async def on_again_date(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    max_date = today + timedelta(days=30)

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"Выберите дату (доступно с {today.strftime('%d.%m.%Y')} по {max_date.strftime('%d.%m.%Y')}):",
        reply_markup=await _calendar().start_calendar(),
    )
    await callback.answer()
