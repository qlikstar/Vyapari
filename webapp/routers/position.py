from typing import List

from fastapi import APIRouter

from dao.position import list_positions, get_position
from webapp.routers.common import PositionModel

router_position = APIRouter(
    prefix="/position",
    tags=["position"]
)


@router_position.get("/", response_model=List[PositionModel],
                     summary="List of positions",
                     description="Returns all positions")
async def get_all_positions():
    return list_positions()


@router_position.get("/view/{id}", response_model=PositionModel, summary="Returns a single position")
async def view(id: int):
    return get_position(id)
