import asyncio
import logging
import random
from collections import defaultdict
from datetime import date
from html import escape

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

from celery_app.app import celery
from tg_bot.bot_settings import settings
from tg_bot.service import subscriptions as subs
from tg_bot.service.client import ask_backend
from tg_bot.utils.formatters import format_train, format_trains, split_message
from tg_bot.keyboards.keyboards import build_buy_inline

log = logging.getLogger(__name__)


async def _send(
    bot: Bot, chat_id: int, chunks: list[str], reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    try:
        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1      # кнопки только под последним куском
            await bot.send_message(
                chat_id, chunk, parse_mode="HTML", reply_markup=reply_markup if is_last else None
            )
    except TelegramForbiddenError:        # пользователь заблокировал бота
        subs.remove_chat(chat_id)
        log.info("Чат %s заблокировал бота, подписки удалены", chat_id)
    except Exception:
        log.exception("Не удалось отправить сообщение в чат %s", chat_id)


def _build_chunks(sub: dict, dep: str, arr: str, d: str, resp: dict) -> list[str]:
    """Текст рассылки для одной подписки: рейс из подписки либо (старые подписки) всё направление."""
    route = f"{escape(dep.replace('+', ' '))} → {escape(arr.replace('+', ' '))}, {d}"
    wanted = sub.get("train_number") or ""
    if not wanted:       # подписки, оформленные до появления выбора рейса
        return split_message(f"🔔 <b>{route}</b>\n\n" + format_trains(resp))

    trains = resp.get("trains", []) if isinstance(resp, dict) else []
    mine = [t for t in trains if subs.norm_train_number(str(t.get("train_number", ""))) == wanted]
    if mine:
        body = "\n\n".join(format_train(t) for t in mine)
    else:
        body = (
            f"🚆 <b>№ {escape(wanted)}</b>: в выдаче нет. "
            "Скорее всего, билетов не осталось (или поезд не ходит в эту дату)."
        )
    return split_message(f"🔔 <b>№ {escape(wanted)}</b> · {route}\n\n" + body)


async def _run() -> None:
    subs.init_db()
    subs.delete_expired(date.today().isoformat())

    due = subs.claim_due()
    if not due:
        return

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for sub in due:
        groups[(sub["dep"], sub["arr"], sub["trip_date"])].append(sub)

    bot = Bot(token=settings.bot_token.get_secret_value())
    try:
        for i, ((dep, arr, trip_date), group) in enumerate(groups.items()):
            if i:
                await asyncio.sleep(random.uniform(1, 3))   # не долбим pass.rw.by
            try:
                resp = await ask_backend(
                    {"dep_station": dep, "arr_station": arr, "trip_date": trip_date}
                )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log.warning("Пропускаю %s → %s (%s): %s", dep, arr, trip_date, e)
                subs.postpone([sub["id"] for sub in group], subs.RETRY_DELAY_MIN)
                continue

            d = date.fromisoformat(trip_date).strftime("%d.%m.%Y")
            buy_kb = build_buy_inline(resp.get("order_url") if isinstance(resp, dict) else None)
            for sub in group:
                await _send(bot, sub["chat_id"], _build_chunks(sub, dep, arr, d, resp), buy_kb)

    finally:
        await bot.session.close()


@celery.task(name="celery_app.tasks.send_subscriptions", ignore_result=True)
def send_subscriptions():
    asyncio.run(_run())
