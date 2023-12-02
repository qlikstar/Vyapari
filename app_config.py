import importlib
import logging
import threading
from datetime import datetime, timedelta
from enum import Enum
from time import sleep

import schedule
from kink import inject, di

from core.database import Database
from core.schedule import SafeScheduler, JobRunType
from scheduled_jobs.post_run_steps import PostRunSteps
from scheduled_jobs.pre_run_steps import PreRunSteps
from scheduled_jobs.runtime_steps import RuntimeSteps
from services.order_service import OrderService
from services.util import load_app_variables

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BEFORE_MARKET_OPEN = '06:30'
START_TRADING = "08:00"
STOP_TRADING = "12:00"
MARKET_CLOSE = "13:00"


class Frequency(Enum):
    DAILY = 24 * 60 * 60
    MIN_1 = 60
    MIN_5 = 300
    MIN_10 = 600
    MIN_30 = 1800
    HOURLY = 3600


@inject
class AppConfig(object):

    def __init__(self):
        self.strategy_name = load_app_variables("STRATEGY")
        self.adhoc_run: bool = load_app_variables("ADHOC_RUN")
        strategy_class = getattr(importlib.import_module(f"strategies.{self.strategy_name}"), self.strategy_name)
        self.strategy = strategy_class()

        self.database: Database = di[Database]
        self.order_service: OrderService = di[OrderService]
        self.pre_run_steps: PreRunSteps = di[PreRunSteps]
        self.runtime_steps: RuntimeSteps = di[RuntimeSteps]
        self.post_run_steps: PostRunSteps = di[PostRunSteps]
        self.schedule: SafeScheduler = di[SafeScheduler]

    def get_strategy(self):
        return self.strategy_name

    def start(self):
        self.schedule.every(Frequency.MIN_1.value).seconds.do(run_threaded, self.register_heartbeat) \
            .tag(JobRunType.HEARTBEAT)

        logger.info("Scheduling jobs... ")
        self._schedule_daily_jobs()

        while True:
            self.schedule.run_pending()
            sleep(10)  # change this if any of the above jobs are more frequent

    '''Clears only DAILY jobs'''

    def cancel(self):
        logger.info("Cancelling scheduler service... ")
        self._cancel_jobs(JobRunType.STANDARD)

    '''Clears both HEARTBEAT and DAILY jobs'''

    def cancel_all(self):
        self.cancel()
        self.schedule.clear()

    def restart(self):
        logger.info("Restarting scheduler service... ")
        self.cancel()
        self._schedule_daily_jobs()

    def get_all_schedules(self) -> list[schedule.Job]:
        return self.schedule.get_jobs()

    def initialize_and_run_once(self, sleep_next_x_seconds, until_time):
        self.init_run()
        self.runtime_steps.run(sleep_next_x_seconds, until_time)
        self.strategy.run(sleep_next_x_seconds, until_time)
        return schedule.CancelJob  # Runs once and kills itself

    def init_run(self):
        logger.info(f"Initializing trader ... Running strategy: {self.strategy_name}")
        self.pre_run_steps.show_configuration()
        self.strategy.init_data()

    def run_before_market_close(self):
        self.order_service.close_all()

    def run_after_market_close(self):
        self.post_run_steps.show_portfolio_details()

    def register_heartbeat(self) -> None:
        self.database.ping()
        logger.info(f"Registering heartbeat ... ")

    def _schedule_daily_jobs(self):

        # Needed for testing and adhoc runs
        now_plus_30 = datetime.now() + timedelta(seconds=61)
        at_time = f"{now_plus_30.hour:02d}:{now_plus_30.minute:02d}"
        logger.info(f"Run once jobs start at: {at_time}")

        daily_jobs = [
            (START_TRADING, self.runtime_steps.run, Frequency.MIN_30.value, MARKET_CLOSE),
            (BEFORE_MARKET_OPEN, self.init_run),
            (START_TRADING, self.strategy.run, Frequency.MIN_10.value, STOP_TRADING),
            # (STOP_TRADING, self.app_config.run_before_market_close),
            (MARKET_CLOSE, self.run_after_market_close),
        ]

        if self._is_within_trading_window():
            daily_jobs.append((at_time, self.initialize_and_run_once, Frequency.MIN_10.value, STOP_TRADING))
        elif self.adhoc_run:
            daily_jobs.append((at_time, self.initialize_and_run_once, Frequency.MIN_10.value, "23:59"))

        for time, func, *args in daily_jobs:
            self.schedule.every().day.at(time).do(func, *args).tag(JobRunType.STANDARD)

        logger.info("***** --- Jobs have been scheduled --- *****")
        [logger.info(s) for s in self.get_all_schedules()]

    @staticmethod
    def _is_within_trading_window() -> bool:
        start_trading_time = datetime.strptime(START_TRADING, '%H:%M').time()
        stop_trading_time = datetime.strptime(STOP_TRADING, '%H:%M').time()
        current_time = datetime.now().time()
        return start_trading_time < current_time < stop_trading_time

    def _cancel_jobs(self, tag):
        for job in self.schedule.get_jobs(tag):
            logger.info(f"Tag: {tag} \tCancelling job: {job}")
            self.schedule.cancel_job(job)
        self.schedule.clear(tag)


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()
