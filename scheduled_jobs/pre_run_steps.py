import logging

from alpaca.trading import TradeAccount
from kink import di, inject

from services.account_service import AccountService
from services.notification_service import Notification
from services.util import load_app_variables

logger = logging.getLogger(__name__)


@inject
class PreRunSteps(object):
    def __init__(self):
        self.account_service: AccountService = di[AccountService]
        self.notification: Notification = di[Notification]

    def show_configuration(self):
        logger.info("Running: pre run steps ...")
        account: TradeAccount = self.account_service.get_account_details()
        strategy_name = load_app_variables("STRATEGY")

        msg = "Starting Vyapari with ... \n"
        msg += "*********************************************\n"
        msg += f"Strategy            : {strategy_name:<20}\n"
        msg += f"Account Number      : {account.account_number:<20}\n"
        msg += f"Account Status      : {account.status.value:<20}\n"
        msg += f"Portfolio Value     : ${float(account.portfolio_value):>11.2f}\n"
        msg += f"Buying power        : ${float(account.buying_power):>11.2f}\n"
        msg += f"Account Multiplier  : {int(account.multiplier):>12}\n"
        msg += "*********************************************\n"
        self.notification.notify(msg)

