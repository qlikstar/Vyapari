import asyncio
import logging
import threading
from _datetime import timedelta
from datetime import datetime
from time import sleep

from kink import di

from app_config import AppConfig
from core.schedule import SafeScheduler, FrequencyTag

logger = logging.getLogger(__name__)

BEFORE_MARKET_OPEN = '06:30'
START_TRADING = "07:01"
STOP_TRADING = "11:55"
MARKET_CLOSE = "12:00"


class SchedulerService(object):
    def __init__(self):
        self.app_config: AppConfig = di[AppConfig]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.schedule.every(10).seconds.do(self.run_threaded, self.app_config.register_heartbeat) \
            .tag(FrequencyTag.HEARTBEAT)

    def start(self):
        logger.info("Scheduling jobs... ")

        if self._is_within_valid_duration():
            self._run_jobs_once()

        ''' Run this when you need to download the data ONLY'''
        # self._run_temp_job()

        self.schedule.every().day.at(BEFORE_MARKET_OPEN).do(self.app_config.initialize).tag(FrequencyTag.DAILY)
        self.schedule.every().day.at(START_TRADING).do(self.app_config.run_strategy, 60,
                                                       STOP_TRADING).tag(FrequencyTag.DAILY)
        self.schedule.every().day.at(START_TRADING).do(self.app_config.show_current_holdings, 600,
                                                       MARKET_CLOSE).tag(FrequencyTag.DAILY)

        self.schedule.every().day.at(STOP_TRADING).do(self.app_config.run_before_market_close).tag(FrequencyTag.DAILY)
        self.schedule.every().day.at(MARKET_CLOSE).do(self.app_config.run_after_market_close).tag(FrequencyTag.DAILY)

        while True:
            self.schedule.run_pending()
            sleep(10)  # change this if any of the above jobs are more frequent

    @staticmethod
    def run_threaded(job_func):
        job_thread = threading.Thread(target=job_func)
        job_thread.start()

    def force_sell(self):
        if self._is_within_valid_duration():
            self.app_config.run_before_market_close()

    def cancel(self):
        logger.info("Cancelling scheduler service... ")
        for job in self.schedule.get_jobs(FrequencyTag.DAILY):
            logger.info(f"Tag:{FrequencyTag.DAILY} \tCancelling job: {job}")
            self.schedule.cancel_job(job)
        self.schedule.clear(FrequencyTag.DAILY)

    def cancel_all(self):
        self.cancel()
        self.schedule.clear()

    def restart(self):
        logger.info("Restarting scheduler service... ")
        self.cancel()

        asyncio.get_running_loop().run_in_executor(None, self.start)

    def _run_jobs_once(self):
        now_plus_30 = datetime.now() + timedelta(seconds=61)
        at_time = str(now_plus_30.hour).rjust(2, '0') + ":" + str(now_plus_30.minute).rjust(2, '0')
        logger.info(f"Run once jobs start at: {at_time}")

        self.schedule.every().day.at(at_time).do(self.app_config.initialize_and_run, 60, STOP_TRADING) \
            .tag(FrequencyTag.DAILY)
        self.schedule.every().day.at(at_time).do(self.app_config.show_current_holdings, 600, MARKET_CLOSE) \
            .tag(FrequencyTag.DAILY)
        return self.schedule.cancel_job

    @staticmethod
    def _is_within_valid_duration() -> bool:
        start_trading_time = datetime.strptime(START_TRADING, '%H:%M').time()
        stop_trading_time = datetime.strptime(STOP_TRADING, '%H:%M').time()
        current_time = datetime.now().time()
        if start_trading_time < current_time < stop_trading_time:
            return True
        return False

    # def _run_temp_job(self):
    #     now_plus_30 = datetime.now() + timedelta(seconds=61)
    #     at_time = str(now_plus_30.hour).rjust(2, '0') + ":" + str(now_plus_30.minute).rjust(2, '0')
    #     logger.info(f"Temp run once jobs start at: {at_time}")
    #
    #     self.schedule.every().day.at(at_time).do(self.app_config.initialize).tag(FrequencyTag.DAILY)
    #     return self.schedule.cancel_job
