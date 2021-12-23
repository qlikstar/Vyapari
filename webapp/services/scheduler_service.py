import logging
from datetime import datetime
from time import sleep

from app_config import AppConfig, get_military_time, generate_run_id
from schedules.safe_schedule import SafeScheduler

logger = logging.getLogger(__name__)


class SchedulerService(object):
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.schedule = SafeScheduler()

    def start(self):
        logger.info("Starting safe scheduler service.")
        start_trading = "06:50"
        stop_trading = "12:30"
        end_time = "13:00"
        start_hr, start_min = map(int, start_trading.split(":"))

        # Run this only on weekdays : PST time
        if datetime.today().weekday() < 7:
            military_time_now = get_military_time(datetime.today().hour, datetime.today().minute)

            self.schedule.every(10).seconds.do(generate_run_id)
            self.schedule.every().day.at(start_trading).do(self.app_config.run_initial_steps)

            # Run only during trading hours
            if military_time_now < get_military_time(start_hr, start_min):
                self.schedule.every(1).minutes.until(stop_trading).do(self.app_config.run_strategy)
                self.schedule.every(5).minutes.until(end_time).do(self.app_config.show_current_holdings)

            self.schedule.every().day.at(stop_trading).do(self.app_config.run_before_market_close)
            self.schedule.every().day.at(end_time).do(self.app_config.run_after_market_close)

        while True:
            self.schedule.run_pending()
            sleep(10)  # change this if any of the above jobs are more frequent
