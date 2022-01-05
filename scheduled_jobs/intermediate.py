from colorama import Fore, Style
from kink import di, inject

from core.schedule import SafeScheduler, FrequencyTag
from services.broker_service import Broker
from services.order_service import OrderService


@inject
class Intermediate(object):

    def __init__(self):
        self.schedule = di[SafeScheduler]
        self.order_service: OrderService = di[OrderService]
        self.broker = di[Broker]

    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self._run_singular, sleep_next_x_seconds, until_time, FrequencyTag.TEN_MINUTELY)

    def _run_singular(self):
        self._run_stats()
        self._update_order_status()

    def _run_stats(self):
        total_unrealized_pl = 0
        for count, position in enumerate(self.broker.get_positions()):
            total_unrealized_pl = total_unrealized_pl + float(position.unrealized_pl)
            print(
                f"{(count + 1):<4}: {position.symbol:<5} - ${float(position.current_price):<8}"
                f"{Fore.GREEN if float(position.unrealized_pl) > 0 else Fore.RED}"
                f" -> ${float(position.unrealized_pl):<8}"
                f"% gain: {float(position.unrealized_plpc) * 100:.2f}%"
                f"{Style.RESET_ALL}"
            )

        print("\n============================================")
        print("Total unrealized P/L: ${:.2f}\n\n".format(total_unrealized_pl))

    def _update_order_status(self):
        self.order_service.update_all_open_orders()
