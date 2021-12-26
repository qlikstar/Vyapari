import asyncio
import logging
from _datetime import timedelta
from datetime import datetime
from time import sleep

from kink import di

from app_config import AppConfig
from schedules.safe_schedule import SafeScheduler

logger = logging.getLogger(__name__)

START_TRADING = "06:50"
STOP_TRADING = "12:30"
MARKET_CLOSE = "13:00"
SLEEP_BETWEEN_RUNS_IN_MIN = 1
RUN_UNTIL = datetime.strptime(STOP_TRADING, '%H:%M').time()
DAILY = "DAILY"
HEARTBEAT = "HEARTBEAT"


class SchedulerService(object):
    def __init__(self):
        self.app_config = di[AppConfig]
        self.schedule = di[SafeScheduler]
        self.schedule.every(10).seconds.do(self.app_config.register_heartbeat).tag(HEARTBEAT)

    def start(self, start_trading=START_TRADING):
        logger.info("Scheduling jobs... ")

        # if self._is_within_valid_duration():
        #     self._run_jobs_once()

        self.schedule.every().day.at(start_trading).do(self.app_config.run_strategy,
                                                       SLEEP_BETWEEN_RUNS_IN_MIN, RUN_UNTIL).tag(DAILY)
        self.schedule.every().day.at(start_trading).do(self.app_config.show_current_holdings).tag(DAILY)
        self.schedule.every().day.at(STOP_TRADING).do(self.app_config.run_before_market_close).tag(DAILY)
        self.schedule.every().day.at(MARKET_CLOSE).do(self.app_config.run_after_market_close).tag(DAILY)

        while True:
            self.schedule.run_pending()
            sleep(10)  # change this if any of the above jobs are more frequent

    def force_sell(self):
        if self._is_within_valid_duration():
            self.app_config.run_before_market_close()

    def cancel(self):
        logger.info("Cancelling scheduler service... ")
        for job in self.schedule.get_jobs(DAILY):
            logger.info(f"Tag:{DAILY} \tCancelling job: {job}")
            self.schedule.cancel_job(job)
        self.schedule.clear(DAILY)

    def cancel_all(self):
        self.cancel()
        for job in self.schedule.get_jobs(HEARTBEAT):
            logger.info(f"Tag:{HEARTBEAT} \tCancelling job: {job}")
            self.schedule.cancel_job(job)
        self.schedule.clear(HEARTBEAT)

    def restart(self):
        logger.info("Restarting scheduler service... ")
        self.cancel()

        asyncio.get_running_loop().run_in_executor(None, self.start)

    def _run_jobs_once(self):
        now_plus_30 = datetime.now() + timedelta(seconds=30)
        at_time = str(now_plus_30.hour).rjust(2, '0') + ":" + str(now_plus_30.minute).rjust(2, '0')
        self.schedule.every().day.at(at_time).do(self.app_config.run_strategy,
                                                 SLEEP_BETWEEN_RUNS_IN_MIN, RUN_UNTIL).tag(DAILY)
        self.schedule.every().day.at(at_time).do(self.app_config.show_current_holdings).tag(DAILY)
        return self.schedule.cancel_job

    @staticmethod
    def _is_within_valid_duration() -> bool:
        start_trading_time = datetime.strptime(START_TRADING, '%H:%M').time()
        stop_trading_time = datetime.strptime(STOP_TRADING, '%H:%M').time()
        current_time = datetime.now().time()
        if start_trading_time < current_time < stop_trading_time:
            return True
        return False
