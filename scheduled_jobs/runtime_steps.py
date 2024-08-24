from typing import List

from alpaca.trading import Order
from kink import di, inject

from core.logger import logger
from core.schedule import SafeScheduler, JobRunType
from services.broker_service import Broker
from services.notification_service import Notification
from services.order_service import OrderService


@inject
class RuntimeSteps(object):

    def __init__(self):
        self.schedule = di[SafeScheduler]
        self.order_service: OrderService = di[OrderService]
        self.broker = di[Broker]
        self.notification = di[Notification]

    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self._run_singular, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def _run_singular(self):
        # self.run_stats() # to send current stats updates to the user
        self._update_order_status()

    def _update_order_status(self):
        updated_orders: List[Order] = self.order_service.update_all_open_orders()
        for order in updated_orders:
            if order.status == 'filled':
                logger.info(f"Filled {order.symbol} order {order.side} at ${order.filled_avg_price}")
