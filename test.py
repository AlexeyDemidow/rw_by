from pprint import pprint
import json
import asyncio

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from parse_text import parse_train

from_station = 'Минск-Пассажирский'
to_station = 'Светлогорск-на-Березине'
date = '2026-10-23'

base = 'https://pass.rw.by'
url = '/ru/route'

def get_random_user_agent():
    user_agent = UserAgent()
    return user_agent.random


async def main():
    result = []
    async with httpx.AsyncClient(
            base_url=base,
            timeout=5.0,
            headers={'User-Agent': get_random_user_agent()}
    ) as client:
        r = await client.get(url, params={'from': from_station, 'to': to_station, 'date': date})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        ss = soup.select('div.sch-table__row-wrap')
        for i in ss:
            if 'Выбрать места' in i.text:
                result.append(parse_train(i.text))
    result.append({'order_url': str(r.url)})
    pprint(result)
    # print(json.dumps(result, ensure_ascii=False))
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
