from decimal import Decimal
from pydantic import BaseModel


class SeatOption(BaseModel):
    seats: int | None
    price: Decimal


class Carriage(BaseModel):
    type: str
    options: list[SeatOption]


class Train(BaseModel):
    train_type: str
    train_number: str
    from_station: str
    to_station: str
    dep_time: str | None = None
    dep_station: str | None = None
    arr_time: str | None = None
    arr_station: str | None = None
    duration: str | None = None
    days: str | None = None
    badges: list[str] = []
    carriages: list[Carriage] = []


class TrainsResponse(BaseModel):
    trains: list[Train]
    order_url: str
