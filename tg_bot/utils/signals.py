from aiogram import Router, Bot

from tg_bot.bot_settings import settings

router = Router()


async def start_bot(bot: Bot):
    await bot.send_message(settings.admin_id, text='Бот запущен')


async def stop_bot(bot: Bot):
    await bot.send_message(settings.admin_id, text='Бот остановлен')