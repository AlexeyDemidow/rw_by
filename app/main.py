import logging
from contextlib import asynccontextmanager
from datetime import date

import httpx
from fake_useragent import UserAgent
from fastapi import Depends, FastAPI, HTTPException, Request

from app.config import settings
from app.exceptions import FetchError, ParseError
from rw.service import build_order_url, get_trains
from app.schemas import TrainsResponse

# from_station = 'Минск-Пассажирский'
# from_station = 'Владивосток'
# to_station = 'Светлогорск-на-Березине'
# date = '2026-10-23'

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with httpx.AsyncClient(
        base_url=settings.BASE,
        timeout=httpx.Timeout(15.0),
        headers={"User-Agent": UserAgent().random},
    ) as client:
        application.state.http = client
        yield

app = FastAPI(lifespan=lifespan)


def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


@app.get("/trains", response_model=TrainsResponse)
async def trains(dep_station: str, arr_station: str, trip_date: date,
                 client: httpx.AsyncClient = Depends(get_client)):
    try:
        found = await get_trains(client, dep_station, arr_station, trip_date)
    except FetchError as e:
        code = 404 if e.status_code in (400, 404) else 502
        raise HTTPException(code, str(e))
    except ParseError:
        raise HTTPException(502, "Не удалось разобрать ответ rw.by")
    return TrainsResponse(
        trains=found,
        order_url=build_order_url(settings.BASE, dep_station, arr_station, trip_date),
    )
