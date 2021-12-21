import time
from datetime import datetime

import schedule
import ulid

from schedules.cleanup import CleanUp
from schedules.final_steps import FinalSteps
from schedules.initial_steps import InitialSteps
from schedules.intermediate import Intermediate
from schedules.watchlist import WatchList
from strategies.lw_modified_strategy import LWModified
from utils.broker import AlpacaClient
from utils.notification import Pushover
from utils.util import load_env_variables


class AppConfig(object):

    def __init__(self):
        load_env_variables()
        self.notification = Pushover()
        self.broker = AlpacaClient(self.notification)
        self.watchlist = WatchList()
        self.initial_steps = InitialSteps(self.broker, self.notification)
        self.intermediate = Intermediate(self.broker)
        self.strategy = LWModified(self.broker)
        self.cleanup = CleanUp(self.broker)
        self.final_steps = FinalSteps(self.broker, self.notification)

    def run_initial_steps(self):
        self.initial_steps.show_portfolio_details()
        return self.strategy.initialize()

    def run_strategy(self):
        self.strategy.run()

    def show_current_holdings(self):
        return self.intermediate.run_stats()

    def run_before_market_close(self):
        self.cleanup.close_all_positions()

    def run_after_market_close(self):
        self.final_steps.show_portfolio_details()

    @staticmethod
    def generate_run_id() -> str:
        return ulid.new().str


def get_military_time(hour: int, minute: int) -> int:
    return (hour * 100) + minute


if __name__ == "__main__":

    app_config = AppConfig()
    start_trading = "08:00"
    stop_trading = "12:30"
    end_time = "13:00"
    start_hr, start_min = map(int, start_trading.split(":"))

    # Run this only on weekdays : PST time
    if datetime.today().weekday() < 7:
        military_time_now = get_military_time(datetime.today().hour, datetime.today().minute)

        run_id = app_config.generate_run_id()  # TODO: Add this to Logger
        schedule.every().day.at(start_trading).do(app_config.run_initial_steps)

        # Run only during trading hours
        # if military_time_now > get_military_time(start_hr, start_min):
        schedule.every(1).minutes.until(stop_trading).do(app_config.run_strategy)
        schedule.every(5).minutes.until(end_time).do(app_config.show_current_holdings)

        schedule.every().day.at(stop_trading).do(app_config.run_before_market_close)
        schedule.every().day.at(end_time).do(app_config.run_after_market_close)

    while True:
        schedule.run_pending()
        time.sleep(10)  # change this if ny of the above jobs are more frequent
