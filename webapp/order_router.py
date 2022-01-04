from datetime import datetime, date
from typing import List

from fastapi import APIRouter
from kink import di
from pydantic import BaseModel

from services.order_service import OrderService
from webapp import PeeweeGetterDict


class OrderModel(BaseModel):
    id: str
    parent_id: str
    symbol: str
    side: str
    order_qty: int
    time_in_force: str
    order_class: str
    order_type: str
    trail_percent: float
    trail_price: float
    initial_stop_price: float
    updated_stop_price: float
    # failed_at: datetime
    # filled_at: datetime
    filled_avg_price: float
    filled_qty: float
    hwm: float
    limit_price: float
    # replaced_by: str
    extended_hours: bool
    status: str
    # cancelled_at: datetime
    # expired_at: datetime
    # replaced_at: datetime
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        getter_dict = PeeweeGetterDict


route = APIRouter(
    prefix="/order",
    tags=["order"]
)

order_service: OrderService = di[OrderService]


@route.get("/today/all", response_model=List[OrderModel], summary="All orders", description="Returns all orders")
async def get_all_orders():
    return order_service.get_all_todays_orders()


@route.get("/{for_date}/all", response_model=List[OrderModel], summary="All orders", description="Returns all orders")
async def get_all_orders(for_date: str):
    dt: date = datetime.strptime(for_date, '%Y-%m-%d').date()
    return order_service.get_all_orders(dt)


@route.post("/update", response_model=List[OrderModel], summary="Update saved orders", description="Returns all orders")
async def update_open_orders():
    return order_service.update_all_open_orders()
