from colorama import Fore, Style
from kink import di, inject

from schedules.safe_schedule import SafeScheduler
from services.broker_service import Broker
from services.order_service import OrderService


@inject
class Intermediate(object):

    def __init__(self):
        self.schedule = di[SafeScheduler]
        self.order_service = di[OrderService]
        self.broker = di[Broker]

    def run(self, until_time):
        self.schedule.every(60).seconds.until(until_time).do(self._run_singular)

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
        for order in self.order_service.get_open_orders():
            self.order_service.update_saved_order(order.id)
