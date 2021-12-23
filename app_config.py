import logging

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

logger = logging.getLogger(__name__)


class AppConfig(object):

    def __init__(self):
        load_env_variables()
        self.notification = Pushover()
        self.broker = AlpacaClient()

        self.watchlist = WatchList()
        self.initial_steps = InitialSteps()
        self.intermediate = Intermediate()
        self.strategy = LWModified()
        self.cleanup = CleanUp()
        self.final_steps = FinalSteps()

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


def generate_run_id() -> str:
    run_id = ulid.new().str
    logger.info(f"Generating new run id: {run_id}")
    return run_id


def get_military_time(hour: int, minute: int) -> int:
    return (hour * 100) + minute
