import asyncio
import uvicorn
from fastapi import FastAPI
from kink import di

from app_config import AppConfig
from core.db_tables import db
from core.logger import logger

app = FastAPI(title='Vyapari', description='APIs for Vyapari', version='0.0.1-SNAPSHOT')

app_config = di[AppConfig]
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


@app.get("/")
async def root():
    return {"message": f"Running Vyapari with {app_config.get_strategy()}"}


def startup_event():
    logger.info("Connecting DB ...")
    db.connect()
    loop.run_in_executor(None, app_config.start)


def shutdown_event():
    logger.info("Cancelling all schedulers...")
    app_config.cancel_all()

    logger.info("Closing all DB connections...")
    db.close()

    logger.info("Closing event loop...")
    while loop.is_running():
        try:
            loop.close()
        except RuntimeError as e:
            logger.warning(f"Exception: {e}")
    logger.info("Exited")


from webapp import position_router, scheduler_router, order_router, ui_router

app.include_router(position_router.route)
app.include_router(scheduler_router.route)
app.include_router(order_router.route)
app.include_router(ui_router.route)

app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)
