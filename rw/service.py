from datetime import date
import httpx

from app.config import settings
from rw.client import fetch
from rw.parser import parse_trains
from app.schemas import Train


async def get_trains(client: httpx.AsyncClient, dep: str, arr: str, d: date) -> list[Train]:
    r = await fetch(client, settings.URL, params={"from": dep, "to": arr, "date": d.isoformat()})
    return parse_trains(r.text)


def build_order_url(base: str, dep: str, arr: str, d: date) -> str:
    return str(httpx.URL(base + settings.URL).copy_merge_params(
        {"from": dep, "to": arr, "date": d.isoformat()}
    ))
