import logging
import threading
from datetime import datetime, timedelta
from time import sleep

from kink import di

from app_config import AppConfig
from core.schedule import SafeScheduler, FrequencyTag

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BEFORE_MARKET_OPEN = '06:30'
START_TRADING = "08:00"
STOP_TRADING = "12:00"
MARKET_CLOSE = "13:00"


class SchedulerService:
    def __init__(self):
        self.app_config: AppConfig = di[AppConfig]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self._initialize_heartbeat_job()

    def _initialize_heartbeat_job(self):
        self.schedule.every(10).seconds.do(self.run_threaded, self.app_config.register_heartbeat).tag(
            FrequencyTag.HEARTBEAT)

    def start(self):
        logger.info("Scheduling jobs... ")
        self._schedule_daily_jobs()

        while True:
            self.schedule.run_pending()
            sleep(10)  # change this if any of the above jobs are more frequent

    def _run_jobs_once(self):
        now_plus_30 = datetime.now() + timedelta(seconds=61)
        at_time = f"{now_plus_30.hour:02d}:{now_plus_30.minute:02d}"
        logger.info(f"Run once jobs start at: {at_time}")

        daily_jobs = [
            (at_time, self.app_config.initialize_and_run_once, 86400, STOP_TRADING),
            (at_time, self.app_config.show_current_holdings, 600, MARKET_CLOSE),
        ]

        for time, func, *args in daily_jobs:
            self.schedule.every().day.at(time).do(func, *args).tag(FrequencyTag.DAILY)

    def _schedule_daily_jobs(self):

        now_plus_30 = datetime.now() + timedelta(seconds=61)
        at_time = f"{now_plus_30.hour:02d}:{now_plus_30.minute:02d}"

        daily_jobs = [
            (BEFORE_MARKET_OPEN, self.app_config.initialize),
            # (START_TRADING, self.app_config.run_strategy, 60, STOP_TRADING),
            (at_time, self.app_config.show_current_holdings, 600, MARKET_CLOSE),
            # (STOP_TRADING, self.app_config.run_before_market_close),
            (MARKET_CLOSE, self.app_config.run_after_market_close),
        ]

        # Needed for testing and adhoc runs
        if self._is_within_valid_duration():
            logger.info(f"Run once jobs start at: {at_time}")
            daily_jobs.append((at_time, self.app_config.initialize_and_run_once, 86400, STOP_TRADING))

        for time, func, *args in daily_jobs:
            self.schedule.every().day.at(time).do(func, *args).tag(FrequencyTag.DAILY)

    @staticmethod
    def run_threaded(job_func):
        job_thread = threading.Thread(target=job_func)
        job_thread.start()

    '''Clears only DAILY jobs'''
    def cancel(self):
        logger.info("Cancelling scheduler service... ")
        self._cancel_jobs(FrequencyTag.DAILY)

    '''Clears HEARTBEAT and DAILY jobs'''
    def cancel_all(self):
        self.cancel()
        self.schedule.clear()

    def restart(self):
        logger.info("Restarting scheduler service... ")
        self.cancel()
        self._schedule_daily_jobs()

    @staticmethod
    def _is_within_valid_duration() -> bool:
        start_trading_time = datetime.strptime(START_TRADING, '%H:%M').time()
        stop_trading_time = datetime.strptime(STOP_TRADING, '%H:%M').time()
        current_time = datetime.now().time()
        return start_trading_time < current_time < stop_trading_time

    def _cancel_jobs(self, tag):
        for job in self.schedule.get_jobs(tag):
            logger.info(f"Tag: {tag} \tCancelling job: {job}")
            self.schedule.cancel_job(job)
        self.schedule.clear(tag)
