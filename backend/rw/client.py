import asyncio
import logging
import random

import httpx

from backend.app.exceptions import FetchError, RETRYABLE

log = logging.getLogger(__name__)


async def fetch(client: httpx.AsyncClient, url: str, *, params=None,
                retries: int = 3, backoff: float = 1.5) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"HTTP {r.status_code}", request=r.request, response=r
                )
            if r.status_code >= 400:
                raise FetchError(f"HTTP {r.status_code}", r.status_code)
            return r
        except RETRYABLE as e:
            last_exc = e
            log.warning("Попытка %d/%d для %s: %s", attempt, retries, url, e)
            if attempt < retries:
                await asyncio.sleep(backoff ** attempt + random.random() * 0.5)
    raise FetchError(f"Не удалось получить {url}") from last_exc
