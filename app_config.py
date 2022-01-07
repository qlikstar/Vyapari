import asyncio
import logging

from kink import inject, di

from scheduled_jobs.cleanup import CleanUp
from scheduled_jobs.final_steps import FinalSteps
from scheduled_jobs.initial_steps import InitialSteps
from scheduled_jobs.intermediate import Intermediate
from scheduled_jobs.watchlist import WatchList
from services.broker_service import AlpacaClient
from services.notification_service import Notification
from services.order_service import OrderService
from services.position_service import PositionService
from services.util import load_env_variables
from strategies.lw_breakout_strategy import LWBreakout

logger = logging.getLogger(__name__)


@inject
class AppConfig(object):

    def __init__(self):
        load_env_variables()
        self.notification = di[Notification]
        self.broker = AlpacaClient()
        self.position_service = PositionService()
        self.order_service = OrderService()

        self.watchlist = WatchList()
        self.initial_steps = InitialSteps()
        self.intermediate = Intermediate()
        self.strategy = LWBreakout()
        self.cleanup = CleanUp()
        self.final_steps = FinalSteps()

    def initialize(self):
        logger.info("Initializing trader ...")
        self.initial_steps.show_portfolio_details()
        self.strategy.init_data()

    def run_strategy(self, sleep_next_x_seconds, until_time):
        if self.broker.is_market_open():
            self.strategy.run(sleep_next_x_seconds, until_time)
        else:
            logger.info("Market is closed today!")

    def initialize_and_run(self, sleep_next_x_seconds, until_time):
        self.initialize()
        self.run_strategy(sleep_next_x_seconds, until_time)

    def show_current_holdings(self, sleep_next_x_seconds, until_time):
        if self.broker.is_market_open():
            return self.intermediate.run(sleep_next_x_seconds, until_time)

    def run_before_market_close(self):
        self.cleanup.close_all_positions()

    def run_after_market_close(self):
        self.final_steps.show_portfolio_details()

    @staticmethod
    def register_heartbeat() -> None:
        logger.info(f"Registering heartbeat ... ")
