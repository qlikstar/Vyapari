import asyncio
import logging

from fastapi import FastAPI

from app_config import AppConfig
from dao.base import conn
from webapp.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

app = FastAPI(title='Vyapari', description='APIs for Vyapari', version='0.1')

app_config = AppConfig()
loop = asyncio.get_running_loop()


def scheduler_run():
    scheduler = SchedulerService(app_config)
    scheduler.start()


@app.get("/")
async def root():
    return {"message": "Running Vyapari! ..."}


@app.on_event("startup")
async def startup():
    logger.info("Connecting DB ...")
    if conn.is_closed():
        conn.connect()

    loop.run_in_executor(None, scheduler_run)


@app.on_event("shutdown")
async def shutdown():
    logger.info("Closing DB connection...")
    if not conn.is_closed():
        conn.close()
    if not loop.is_closed():
        loop.close()


from webapp.routers import position
app.include_router(position.router_position)
