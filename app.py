import asyncio
import logging

from fastapi import FastAPI
from kink import di

from app_config import AppConfig
from dao.base import conn
from webapp.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

app = FastAPI(title='Vyapari', description='APIs for Vyapari', version='0.0.1-SNAPSHOT')

app_config = AppConfig()
loop = asyncio.get_running_loop()

scheduler_service = SchedulerService()
di[SchedulerService] = scheduler_service


@app.get("/")
async def root():
    return {"message": "Running Vyapari! ..."}


@app.on_event("startup")
async def startup():
    logger.info("Connecting DB ...")
    if conn.is_closed():
        conn.connect()

    loop.run_in_executor(None, scheduler_service.start)


@app.on_event("shutdown")
async def shutdown():
    scheduler_service.cancel_all()
    logger.info("Closing DB connection...")
    if not conn.is_closed():
        conn.close()

    logger.info("Closing event loop...")
    while loop.is_running():
        try:
            loop.close()
        except RuntimeError as e:
            logger.warning(f"Exception: {e}")
    logger.info("Exited")


from webapp.routers import position_router, scheduler_router, callback_router

app.include_router(position_router.route)
app.include_router(scheduler_router.route)
app.include_router(callback_router.route)

# if __name__ == "__main__":
#     uvicorn.run(host="0.0.0.0", port=8000)
