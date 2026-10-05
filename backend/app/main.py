import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

import httpx
from fake_useragent import UserAgent
from fastapi import Depends, FastAPI, HTTPException, Query, Request

from backend.app.config import settings
from backend.app.exceptions import FetchError, ParseError
from backend.app.schemas import TrainsResponse
from backend.rw.service import build_order_url, get_trains

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with httpx.AsyncClient(
        base_url=settings.BASE,
        timeout=httpx.Timeout(15.0),
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),  # пока условные значения
        headers={"User-Agent": UserAgent().random},
    ) as client:
        application.state.http = client
        yield


app = FastAPI(lifespan=lifespan)


def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


Client = Annotated[httpx.AsyncClient, Depends(get_client)]

DepStation = Annotated[
    str,
    Query(
        min_length=1,
        description="Название станции отправления.",
        openapi_examples={
            "minsk": {
                "summary": "Минск",
                "value": "Минск-Пассажирский",
            },
            "brest": {
                "summary": "Брест",
                "value": "Брест-Центральный",
            },
        },
    ),
]

ArrStation = Annotated[
    str,
    Query(
        min_length=1,
        description="Название станции прибытия.",
        openapi_examples={
            "svetlogorsk": {
                "summary": "Светлогорск",
                "value": "Светлогорск-на-Березине",
            },
            "gomel": {
                "summary": "Гомель",
                "value": "Гомель",
            },
        },
    ),
]

TripDate = Annotated[
    date,
    Query(
        description="Дата поездки (YYYY-MM-DD).",
        openapi_examples={
            "sample": {
                "summary": "Пример даты",
                "value": "2026-10-23",
            },
        },
    ),
]


@app.get(
    "/trains",
    tags=['Расписание'],
    response_model=TrainsResponse,
    summary="Список поездов по маршруту",
    description="Возвращает поезда по дате, станции отправления и станции прибытия.",
)
async def trains(
    dep_station: DepStation,
    arr_station: ArrStation,
    trip_date: TripDate,
    client: Client,
):
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
