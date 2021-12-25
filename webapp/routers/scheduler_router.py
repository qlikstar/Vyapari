from fastapi import APIRouter
from kink import di

from webapp.services.scheduler_service import SchedulerService

route = APIRouter(
    prefix="/scheduler",
    tags=["scheduler"]
)

scheduler_service = di[SchedulerService]


@route.post("/cancel", summary="Cancel running schedule", description="Cancel running schedule")
async def cancel_running_schedule():
    scheduler_service.cancel()
    return {"status": "cancelled"}


@route.post("/restart", summary="Restart running schedule", description="Restart running schedule")
async def restart_running_schedule():
    scheduler_service.restart()
    return {"status": "restarted"}
