import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from kink import di

from app_config import AppConfig
from core.db_tables import db
from services.scheduler_service import SchedulerService
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

app = FastAPI(title='Vyapari', description='APIs for Vyapari', version='0.0.1-SNAPSHOT')
templates = Jinja2Templates(directory="templates")

app_config = AppConfig()
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

scheduler_service = SchedulerService()
di[SchedulerService] = scheduler_service


@app.get("/")
async def root():
    return {"message": "Running Vyapari! ..."}


@app.on_event("startup")
async def startup():
    logger.info("Connecting DB ...")
    db.connect()

    loop.run_in_executor(None, scheduler_service.start)


@app.on_event("shutdown")
async def shutdown():
    logger.info("Cancelling all schedulers...")
    scheduler_service.cancel_all()

    logger.info("Closing all DB connections...")
    db.close()

    logger.info("Closing event loop...")
    while loop.is_running():
        try:
            loop.close()
        except RuntimeError as e:
            logger.warning(f"Exception: {e}")
    logger.info("Exited")


from webapp import callback_router, position_router, scheduler_router, order_router, ui_router

app.include_router(position_router.route)
app.include_router(scheduler_router.route)
app.include_router(callback_router.route)
app.include_router(order_router.route)
app.include_router(ui_router.route)

if __name__ == "__main__":
    uvicorn.run(host="0.0.0.0", port=8000)
