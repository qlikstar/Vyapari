import logging

from kink import inject

from schedules.cleanup import CleanUp
from schedules.final_steps import FinalSteps
from schedules.initial_steps import InitialSteps
from schedules.intermediate import Intermediate
from schedules.watchlist import WatchList
from strategies.lw_modified_strategy import LWModified
from services.broker_service import AlpacaClient
from services.notification_service import Pushover
from services.util import load_env_variables
from services.position_service import PositionService

logger = logging.getLogger(__name__)


@inject
class AppConfig(object):

    def __init__(self):
        load_env_variables()
        self.notification = Pushover()
        self.broker = AlpacaClient()
        self.position_service = PositionService()

        self.watchlist = WatchList()
        self.initial_steps = InitialSteps()
        self.intermediate = Intermediate()
        self.strategy = LWModified()
        self.cleanup = CleanUp()
        self.final_steps = FinalSteps()

    def run_strategy(self, sleep_between_runs_in_min, until):

        if self.broker.is_market_open():
            self.initial_steps.show_portfolio_details()
            self.strategy.initialize()
            self.strategy.run(sleep_between_runs_in_min, until)
        else:
            logger.info("Market is closed today!")

    def show_current_holdings(self, sleep_between_runs_in_min, until):
        if self.broker.is_market_open():
            return self.intermediate.run_stats(sleep_between_runs_in_min, until)

    def run_before_market_close(self):
        self.cleanup.close_all_positions()

    def run_after_market_close(self):
        self.final_steps.show_portfolio_details()

    @staticmethod
    def register_heartbeat() -> None:
        logger.info(f"Registering heartbeat ... ")
