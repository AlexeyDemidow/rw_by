import logging
from pprint import pprint
import json
import asyncio

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from httpx import Timeout, Limits

from exeptions import FetchError, RETRYABLE
from parse_text import parse_train

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("parser.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("rw_parser")

from_station = 'Минск-Пассажирский'
to_station = 'Светлогорск-на-Березине'
date = '2026-10-23'

base = 'https://pass.rw.by'
url = '/ru/route'

timeout = Timeout(15.0)


async def fetch(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    retries: int = 3,
    backoff: float = 1.5,
) -> httpx.Response:
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            r = await client.get(url, params=params)

            if 500 <= r.status_code < 600:
                raise httpx.HTTPStatusError(
                    f"server error {r.status_code}",
                    request=r.request,
                    response=r,
                )

            if 400 <= r.status_code < 500:
                log.warning("HTTP %s на %s", r.status_code, r.url)
                raise FetchError(f"HTTP {r.status_code} для {r.url}")

            return r

        except (httpx.HTTPStatusError, *RETRYABLE) as e:
            last_exc = e
            log.warning("Попытка %d/%d для %s не удалась: %s", attempt, retries, url, e)
            if attempt < retries:
                await asyncio.sleep(backoff ** attempt)

    log.error("Все %d попыток для %s провалились", retries, url)
    raise FetchError(f"Не удалось получить {url}") from last_exc

def get_random_user_agent():
    user_agent = UserAgent()
    return user_agent.random

def parse_trains(html: str) -> list[dict]:
    """Извлекает поезда из HTML. Сломанные строки пропускает с логом."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("div.sch-table__row-wrap")

    trains = []
    for row in rows:
        if "Выбрать места" not in row.text:
            continue
        try:
            trains.append(parse_train(row.text))
        except Exception as e:
            log.warning("Не удалось разобрать строку: %s", e)
            continue
    return trains


async def check_route(
    client: httpx.AsyncClient,
    from_station: str,
    to_station: str,
    date: str,
) -> list[dict] | None:
    """Возвращает список поездов или None, если проверить не удалось."""
    try:
        r = await fetch(
            client,
            URL,
            params={"from": from_station, "to": to_station, "date": date},
        )
    except FetchError as e:
        log.error("Маршрут %s → %s (%s): %s", from_station, to_station, date, e)
        return None

    try:
        trains = parse_trains(r.text)
    except Exception as e:
        log.exception("Ошибка парсинга %s", r.url)
        return None

    if not trains:
        log.info("Поездов не найдено: %s", r.url)

    return trains


async def main():
    async with httpx.AsyncClient(
        base_url=BASE,
        timeout=timeout,
        headers={"User-Agent": user_agent.random},
    ) as client:
        trains = await check_route(client, from_station, to_station, date)

    result = {
        "trains": trains or [],
        "order_url": str(
            httpx.URL(BASE + URL).copy_merge_params(
                {"from": from_station, "to": to_station, "date": date}
            )
        ),
    }
    pprint(result)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
