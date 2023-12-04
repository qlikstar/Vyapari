import logging
from typing import List

from alpaca.trading import Order
from colorama import Fore, Style
from kink import di, inject

from core.schedule import SafeScheduler, JobRunType
from services.broker_service import Broker
from services.notification_service import Notification
from services.order_service import OrderService

logger = logging.getLogger(__name__)


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
        self.run_stats()
        self._update_order_status()

    def run_stats(self):
        total_unrealized_pl = 0

        pl_msg = "***====== Total unrealized (P/L)  ======***\n"
        pl_msg += "No. Symbol  Invest Amt  PL (USD)   PL (%)\n"
        pl_msg += "==========================================\n"
        log_msg = pl_msg
        for count, position in enumerate(self.broker.get_positions()):
            total_unrealized_pl = total_unrealized_pl + float(position.unrealized_pl)
            log_msg += (
                f"{(count + 1):<3} "
                f"{position.symbol:<7}  "
                f"${float(position.cost_basis):>7.2f} "
                f"{Fore.GREEN if float(position.unrealized_pl) > 0 else Fore.RED}  "
                f"${float(position.unrealized_pl):>7.2f} "  # Fixed formatting
                f"{float(position.unrealized_plpc) * 100:>6.2f}%"
                f"{Style.RESET_ALL}\n"
            )
            pl_msg += (
                f"{(count + 1):<3} "
                f"{position.symbol:<7}  "
                f"${float(position.cost_basis):>7.2f}  "
                f"${float(position.unrealized_pl):>7.2f} "
                f"{float(position.unrealized_plpc) * 100:>6.2f}%\n"
            )

        log_msg += "==========================================\n"
        pl_msg += "==========================================\n"

        log_msg += "Total unrealized P/L: ${:.2f}\n".format(total_unrealized_pl)
        pl_msg += "Total unrealized P/L: ${:.2f}\n".format(total_unrealized_pl)
        print(log_msg)
        self.notification.notify(pl_msg)

    def _update_order_status(self):
        updated_orders: List[Order] = self.order_service.update_all_open_orders()
        for order in updated_orders:
            if order.status == 'filled':
                logger.info(f"Filled {order.symbol} order {order.side} at ${order.filled_avg_price}")
