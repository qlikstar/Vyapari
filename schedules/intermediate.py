import time

from colorama import Fore, Style
from kink import di

from utils.broker import Broker
from webapp.services.position_service import PositionService

UNTIL_NEXT_TIME_IN_MINS = 390
SLEEP_IN_MINS = 10


class Intermediate(object):

    def __init__(self):
        self.broker = di[Broker]
        self.position_service = di[PositionService]

    def run_stats(self):

        time_end = time.time() + (UNTIL_NEXT_TIME_IN_MINS * 60)
        while time.time() < time_end:
            self._run_stats_singular()
            time.sleep(SLEEP_IN_MINS * 60)

    def _run_stats_singular(self):
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
        self.position_service.update_current_positions()
