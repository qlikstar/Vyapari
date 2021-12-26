from datetime import datetime, date
from typing import List

from fastapi import APIRouter
from kink import di
from pydantic import BaseModel

from utils.broker import Broker
from webapp.routers import PeeweeGetterDict
from webapp.services.position_service import PositionService


class PositionModel(BaseModel):
    run_date: date
    symbol: str
    side: str
    qty: int
    entry_price: float
    market_price: float
    lastday_price: float
    created_at: datetime

    class Config:
        orm_mode = True
        getter_dict = PeeweeGetterDict


route = APIRouter(
    prefix="/position",
    tags=["position"]
)

position_service = PositionService(di[Broker])


@route.get("/", response_model=List[PositionModel],
           summary="List of positions",
           description="Returns all positions")
async def get_all_positions():
    return position_service.update_and_get_current_positions()


@route.get("/id/{sym}", response_model=PositionModel, summary="Returns a single position")
async def view(sym: str):
    return position_service.get_position(sym)
