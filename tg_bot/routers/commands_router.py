import asyncio
from datetime import datetime, timedelta

import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from tg_bot.keyboards.keyboards import (
    ALL_STATIONS,
    MAX_RESULTS,
    StationCb,
    build_stations_inline,
    station_title,
    build_again_inline,
    build_route_actions_inline,
    build_unsub_inline, search_stations, build_search_results_inline, build_interval_inline
)
from tg_bot.service import subscriptions
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


@router.callback_query(StationCb.filter(F.action == "pick"))
async def on_pick(callback: CallbackQuery, callback_data: StationCb, state: FSMContext):
    await state.set_state(BotStates.start)  # выходим из режима поиска, иначе следующий текст снова станет запросом
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
            reply_markup=build_stations_inline(step="to", src=callback_data.value),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # выбор станции прибытия
    dep = ALL_STATIONS[callback_data.src]
    arr = ALL_STATIONS[callback_data.value]

    await state.update_data(dep=dep, arr=arr)

    await callback.message.edit_text(
        f"Маршрут: <b>{station_title(callback_data.src)} → {station_title(callback_data.value)}</b>\n"
        f"Дата: {datetime.strptime(trip_date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n\n"
        "Что сделать?",
        reply_markup=build_route_actions_inline(),
        parse_mode="HTML",
    )
    await callback.answer()


def _stations_prompt(step: str, src: int) -> str:
    if step == "from":
        return "Выберите станцию отправления:"
    return f"Отправление: <b>{station_title(src)}</b>\nВыберите станцию прибытия:"


@router.callback_query(StationCb.filter(F.action == "search"))
async def on_search(callback: CallbackQuery, callback_data: StationCb, state: FSMContext):
    await state.set_state(BotStates.searching)
    await state.update_data(search_step=callback_data.step, search_src=callback_data.src)

    what = "отправления" if callback_data.step == "from" else "прибытия"
    await callback.message.edit_text(
        f"Введите название станции {what} или его часть (например, «полоц»):",
        reply_markup=build_search_results_inline([], callback_data.step, callback_data.src),
    )
    await callback.answer()


@router.callback_query(StationCb.filter(F.action == "back"))
async def on_search_back(callback: CallbackQuery, callback_data: StationCb, state: FSMContext):
    await state.set_state(BotStates.start)
    await callback.message.edit_text(
        _stations_prompt(callback_data.step, callback_data.src),
        reply_markup=build_stations_inline(callback_data.step, callback_data.src),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BotStates.searching, F.text, ~F.text.startswith("/"))
async def on_station_query(message: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("search_step", "from")
    src = data.get("search_src", -1)

    found = search_stations(message.text, exclude=src)
    if not found:
        await message.answer(
            "Ничего не нашёл. Введите хотя бы 2 буквы названия или его часть.",
            reply_markup=build_search_results_inline([], step, src),
        )
        return

    text = "Найденные станции:"
    if len(found) > MAX_RESULTS:
        text = f"Найдено {len(found)}, показаны первые {MAX_RESULTS}. Уточните запрос или выберите станцию:"
    await message.answer(text, reply_markup=build_search_results_inline(found[:MAX_RESULTS], step, src))


async def _route_from_state(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trip_date, dep, arr = data.get("trip_date"), data.get("dep"), data.get("arr")
    if not (trip_date and dep and arr):
        await callback.message.answer("⚠️ Сначала выберите дату и маршрут через /start")
        await callback.answer()
        return None
    return trip_date, dep, arr


@router.callback_query(F.data == "route:now")
async def on_route_now(callback: CallbackQuery, state: FSMContext):
    route = await _route_from_state(callback, state)
    if not route:
        return
    trip_date, dep, arr = route

    try:
        response = await ask_backend(payload={
            "dep_station": dep,
            "arr_station": arr,
            "trip_date": trip_date,
        })
    except (aiohttp.ClientError, asyncio.TimeoutError):
        await callback.message.answer(
            "⚠️ Сервер временно недоступен",
            reply_markup=build_again_inline(),
        )
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


@router.callback_query(F.data == "route:sub")
async def on_route_sub(callback: CallbackQuery, state: FSMContext):
    route = await _route_from_state(callback, state)
    if not route:
        return
    # отдельным сообщением, чтобы кнопки «Показать сейчас» / «Присылать регулярно» остались доступны
    await callback.message.answer("Как часто присылать расписание?", reply_markup=build_interval_inline())
    await callback.answer()

    route = await _route_from_state(callback, state)
    if not route:
        return
    trip_date, dep, arr = route

    created = subscriptions.add(callback.message.chat.id, dep, arr, trip_date)
    if created:
        await callback.message.answer(
            f"🔔 Подписка оформлена. Расписание будет приходить каждые "
            f"{subscriptions.SEND_INTERVAL_MIN} мин до даты поездки.\n"
            f"В тестовом режиме приходит каждую минуту (возможность выбора будет позже)\n"
            "Отменить: /subscriptions"
        )
    else:
        await callback.message.answer("Вы уже подписаны на этот маршрут и дату. Отменить: /subscriptions")
    await callback.answer()


@router.message(Command("subscriptions"))
async def cmd_subscriptions(message: Message):
    items = subscriptions.list_for_chat(message.chat.id)
    if not items:
        await message.answer("У вас нет активных подписок.")
        return
    await message.answer("Ваши подписки (нажмите, чтобы отменить):", reply_markup=build_unsub_inline(items))


@router.callback_query(F.data.startswith("unsub:"))
async def on_unsub(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    subscriptions.remove(int(callback.data.split(":")[1]), chat_id)
    items = subscriptions.list_for_chat(chat_id)
    if items:
        await callback.message.edit_reply_markup(reply_markup=build_unsub_inline(items))
    else:
        await callback.message.edit_text("Подписок больше нет.")
    await callback.answer("Подписка отменена")


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
async def on_again_date(callback: CallbackQuery):
    today = datetime.now()
    max_date = today + timedelta(days=30)

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"Выберите дату (доступно с {today.strftime('%d.%m.%Y')} по {max_date.strftime('%d.%m.%Y')}):",
        reply_markup=await _calendar().start_calendar(),
    )
    await callback.answer()
