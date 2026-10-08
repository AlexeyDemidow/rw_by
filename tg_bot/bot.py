import asyncio
import logging

from aiogram import Bot, Dispatcher

from tg_bot.routers import commands_router
from tg_bot.service import subscriptions
from tg_bot.utils.signals import start_bot, stop_bot
from tg_bot.utils.commands import set_commands
from tg_bot.bot_settings import settings

logging.basicConfig(level=logging.INFO)
bot = Bot(token=settings.bot_token.get_secret_value())
dp = Dispatcher()


async def main():
    dp.startup.register(start_bot)
    dp.include_routers(
        commands_router.router,
    )

    dp.shutdown.register(stop_bot)
    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    subscriptions.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())