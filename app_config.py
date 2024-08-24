import importlib
import threading
from datetime import datetime, timedelta
from enum import Enum
from time import sleep
from typing import Optional, Hashable

import schedule
from kink import inject, di

from core.logger import logger
from core.database import Database
from core.schedule import SafeScheduler, JobRunType
from scheduled_jobs.post_run_steps import PostRunSteps
from scheduled_jobs.pre_run_steps import PreRunSteps
from scheduled_jobs.runtime_steps import RuntimeSteps
from services.order_service import OrderService
from services.util import load_app_variables

BEFORE_MARKET_OPEN = '06:30'
START_TRADING = "08:00"
STOP_TRADING = "12:00"
MARKET_CLOSE = "13:00"
MAX_TIME = "23:59"


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
        self.schedule.every(Frequency.MIN_1.value).seconds.do(run_threaded, self.register_heartbeat) \
            .tag(JobRunType.HEARTBEAT)

    def get_strategy(self):
        return self.strategy_name

    def start(self):
        logger.info("Scheduling jobs... ")
        self._schedule_weekday_jobs()
        self._schedule_run_now_jobs()

        while True:
            self.schedule.run_pending()
            sleep(10)  # change this if any of the above jobs are more frequent

    '''
    Clears only DAILY jobs
    '''

    def cancel(self):
        logger.info("Cancelling scheduler service... ")
        for job in self.schedule.get_jobs(JobRunType.STANDARD):
            logger.info(f"Cancelling job: {job}")
            self.schedule.cancel_job(job)

    '''
    Clears both HEARTBEAT and DAILY jobs
    '''

    def cancel_all(self):
        self.cancel()
        self.schedule.clear()

    def restart(self):
        logger.info("Restarting scheduler service... ")
        self.cancel()
        self.start()

    def get_all_schedules(self, tag: Optional[Hashable] = None) -> list[schedule.Job]:
        return self.schedule.get_jobs(tag=tag)

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
        self.post_run_steps.run_stats()
        self.post_run_steps.show_portfolio_details()

    def register_heartbeat(self) -> None:
        self.database.ping()
        logger.info(f"Registering heartbeat ... ")

    def _schedule_weekday_jobs(self):
        weekday_jobs = [
            (START_TRADING, self.runtime_steps.run, Frequency.MIN_30.value, MARKET_CLOSE),
            (BEFORE_MARKET_OPEN, self.init_run),
            (START_TRADING, self.strategy.run, Frequency.MIN_10.value, STOP_TRADING),
            # (STOP_TRADING, self.app_config.run_before_market_close),
            (MARKET_CLOSE, self.run_after_market_close),
        ]

        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for day in weekdays:
            for time, func, *args in weekday_jobs:
                getattr(self.schedule.every(), day).at(time).do(func, *args).tag(JobRunType.STANDARD)

        logger.info("***** --- Weekday Jobs have been scheduled --- *****")
        [logger.info(s) for s in self.get_all_schedules()]

    '''
    Runs only if "ADHOC_RUN" is True or if the service is restarted during an ongoing trading window
    These jobs just run once and then the regular schedule catches up
    '''

    def _schedule_run_now_jobs(self):
        run_now_jobs = []
        is_within_trading_window: bool = self._is_within_trading_window()

        if is_within_trading_window or self.adhoc_run:

            next_minute = datetime.now() + timedelta(seconds=61)
            at_time = f"{next_minute.hour:02d}:{next_minute.minute:02d}"

            if is_within_trading_window:
                logger.info("*** Within trading window ***")
                run_now_jobs.append((at_time, self.initialize_and_run_once, Frequency.MIN_10.value, STOP_TRADING))
            elif self.adhoc_run:
                run_now_jobs.append((at_time, self.initialize_and_run_once, Frequency.MIN_10.value, MAX_TIME))
                logger.info(f"*** Adhoc run flag set to : ***{self.adhoc_run}")
            logger.info(f"Run now jobs start at: {at_time}")

            for time, func, *args in run_now_jobs:
                self.schedule.every().day.at(time).do(func, *args).tag(JobRunType.STANDARD, JobRunType.RUN_NOW)

            logger.info("***** --- Run now Jobs have been scheduled --- *****")
            [logger.info(s) for s in self.get_all_schedules(JobRunType.RUN_NOW)]

    def _is_within_trading_window(self) -> bool:

        if self.order_service.is_market_open():
            start_trading_time = datetime.strptime(START_TRADING, '%H:%M').time()
            stop_trading_time = datetime.strptime(STOP_TRADING, '%H:%M').time()
            current_time = datetime.now().time()
            return start_trading_time < current_time < stop_trading_time
        else:
            return False


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()
