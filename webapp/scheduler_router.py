from fastapi import APIRouter
from kink import di

from app_config import AppConfig

route = APIRouter(
    prefix="/scheduler",
    tags=["scheduler"]
)

app_config = di[AppConfig]


@route.get("/all", summary="Get all schedules", description="Get all schedules")
async def get_all_schedules():
    return [str(s) for s in app_config.get_all_schedules()]


@route.post("/cancel", summary="Cancel running schedule", description="Cancel running schedule")
async def cancel_running_schedule():
    app_config.cancel()
    return {"status": "cancelled"}


@route.post("/restart", summary="Restart running schedule", description="Restart running schedule")
async def restart_running_schedule():
    app_config.restart()
    return {"status": "restarted"}
