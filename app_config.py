import logging
import importlib

from kink import inject, di

from core.database import Database
from scheduled_jobs.cleanup import CleanUp
from scheduled_jobs.final_steps import FinalSteps
from scheduled_jobs.initial_steps import InitialSteps
from scheduled_jobs.intermediate import Intermediate
from services.order_service import OrderService
from services.util import load_app_variables

logger = logging.getLogger(__name__)


@inject
class AppConfig(object):

    def __init__(self):
        self.strategy_name = load_app_variables("strategy")
        strategy_class = getattr(importlib.import_module(f"strategies.{self.strategy_name}"), self.strategy_name)
        self.strategy = strategy_class()

        self.database: Database = di[Database]
        self.order_service = di[OrderService]
        self.initial_steps = di[InitialSteps]
        self.intermediate = di[Intermediate]
        self.cleanup = di[CleanUp]
        self.final_steps = di[FinalSteps]

    def initialize(self):
        logger.info(f"Initializing trader ... Running strategy: {self.strategy_name}")
        self.initial_steps.show_portfolio_details()
        self.strategy.init_data()

    def run_strategy(self, sleep_next_x_seconds, until_time):
        if self.order_service.is_market_open():
            self.strategy.run(sleep_next_x_seconds, until_time)
        else:
            logger.info("Market is closed today!")

    def initialize_and_run(self, sleep_next_x_seconds, until_time):
        self.initialize()
        self.run_strategy(sleep_next_x_seconds, until_time)

    def show_current_holdings(self, sleep_next_x_seconds, until_time):
        if self.order_service.is_market_open():
            return self.intermediate.run(sleep_next_x_seconds, until_time)

    def run_before_market_close(self):
        self.cleanup.close_all_positions()

    def run_after_market_close(self):
        self.final_steps.show_portfolio_details()

    def register_heartbeat(self) -> None:
        self.database.ping()
        logger.info(f"Registering heartbeat ... ")
