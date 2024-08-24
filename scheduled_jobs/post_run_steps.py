from colorama import Fore, Style
from kink import di, inject

from core.logger import logger
from services.account_service import AccountService
from services.broker_service import Broker
from services.notification_service import Notification


@inject
class PostRunSteps(object):

    def __init__(self):
        self.account_service: AccountService = di[AccountService]
        self.notification: Notification = di[Notification]
        self.broker = di[Broker]

    def run_stats(self):
        total_unrealized_pl = 0

        pl_msg = "***====== Total unrealized (P/L)  ======***\n"
        pl_msg += "No. Symbol  Invest Amt  PL (USD)   PL (%)\n"
        pl_msg += "==========================================\n"
        log_msg = pl_msg
        # current_portfolio_value = float(self.broker.get_portfolio().portfolio_value)
        for count, position in enumerate(self.broker.get_positions()):
            total_unrealized_pl = total_unrealized_pl + float(position.unrealized_pl)
            log_msg += (
                f"{(count + 1):<3} "
                f"{position.symbol:<7}  "
                f"${float(position.cost_basis):>7.2f} "
                f"{Fore.GREEN if float(position.unrealized_pl) > 0 else Fore.RED}  "
                f"${float(position.unrealized_pl):>7.2f} "
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

        # log_msg += "Total portfolio value: ${:.2f}\n".format(current_portfolio_value)
        # pl_msg += "Total portfolio value: ${:.2f}\n".format(current_portfolio_value)

        print(log_msg)
        self.notification.notify(pl_msg)

    def show_portfolio_details(self):
        # TODO: delete data folder for today
        portfolio = self.account_service.get_account_details()
        self.notification.notify(f"Final portfolio value: ${float(portfolio.portfolio_value)}")
        logger.info("Completed: Final Steps for the day")
