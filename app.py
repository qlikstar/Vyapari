from fastapi import FastAPI

from app_config import AppConfig
from dao.base import conn

app = FastAPI(title='Vyapari', description='APIs for Vyapari', version='0.1')

app_config = AppConfig()
app_config.bootstrap_di()


@app.get("/")
async def root():
    return {"message": "Running Vyapari! ..."}


@app.on_event("startup")
async def startup():
    print("Connecting DB ...")
    if conn.is_closed():
        conn.connect()


@app.on_event("shutdown")
async def shutdown():
    print("Closing DB connection...")
    if not conn.is_closed():
        conn.close()


from webapp.routers import position

app.include_router(position.router_position)

# @repeat_every(seconds=10)  # checks every 30 seconds if a job is pending
# async def run_scheduled_tasks():
#     print("Running scheduled tasks ... ")
#
#     scheduler.every(3).seconds.do(job)

# Run this only on weekdays : PST time
# if datetime.today().weekday() < 7:
#     military_time_now = get_military_time(datetime.today().hour, datetime.today().minute)
#     print("Time now: {}".format(military_time_now))
#
#     run_id = app_config.generate_run_id()  # TODO: Add this to Logger
#     scheduler.every().day.at(start_trading).do(app_config.run_initial_steps)
#
#     # Run only during trading hours
#     if military_time_now < get_military_time(start_hr, start_min):
#         print("Running strategy ... ")
#         scheduler.every(1).minutes.until(stop_trading).do(app_config.run_strategy)
#         scheduler.every(5).minutes.until(end_time).do(app_config.show_current_holdings)
#
#     scheduler.every().day.at(stop_trading).do(app_config.run_before_market_close)
#     scheduler.every().day.at(end_time).do(app_config.run_after_market_close)

# scheduler.run_pending()
