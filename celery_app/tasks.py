import asyncio
import logging
import random
from collections import defaultdict
from datetime import date
from html import escape

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from celery_app.app import celery
from tg_bot.bot_settings import settings
from tg_bot.service import subscriptions as subs
from tg_bot.service.client import ask_backend
from tg_bot.utils.formatters import format_trains, split_message

log = logging.getLogger(__name__)


async def _send(bot: Bot, chat_id: int, chunks: list[str]) -> None:
    try:
        for chunk in chunks:
            await bot.send_message(chat_id, chunk, parse_mode="HTML")
    except TelegramForbiddenError:        # пользователь заблокировал бота
        subs.remove_chat(chat_id)
        log.info("Чат %s заблокировал бота, подписки удалены", chat_id)
    except Exception:
        log.exception("Не удалось отправить сообщение в чат %s", chat_id)


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
            header = (
                f"🔔 <b>{escape(dep.replace('+', ' '))} → {escape(arr.replace('+', ' '))}</b>, {d}\n\n"
            )
            chunks = split_message(header + format_trains(resp))
            for sub in group:
                await _send(bot, sub["chat_id"], chunks)
    finally:
        await bot.session.close()


@celery.task(name="celery_app.tasks.send_subscriptions", ignore_result=True)
def send_subscriptions():
    asyncio.run(_run())
