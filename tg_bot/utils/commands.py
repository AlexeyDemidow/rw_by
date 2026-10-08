from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Начать работу',
        ),
        BotCommand(
            command='subscriptions',
            description='Мои подписки'
        ),
    ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())
