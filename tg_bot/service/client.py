import aiohttp

from tg_bot.bot_settings import settings


async def ask_backend(payload):
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(settings.backend_url + '/trains', params=payload) as resp:
            resp.raise_for_status()
            return await resp.json()
