import aiohttp

from tg_bot.bot_settings import settings


async def ask_backend(payload):
    async with aiohttp.ClientSession() as session:
        async with session.get(settings.backend_url + '/trains', params=payload) as resp:
            return await resp.json()
