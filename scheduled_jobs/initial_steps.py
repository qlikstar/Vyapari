import logging

from kink import di, inject

from services.account_service import AccountService
from services.notification_service import Notification

logger = logging.getLogger(__name__)


@inject
class InitialSteps(object):
    def __init__(self):  # db, broker
        self.account_service: AccountService = di[AccountService]
        self.notification: Notification = di[Notification]
        self.show_configuration()

    def show_portfolio_details(self):
        portfolio = self.account_service.get_account_details()
        self.notification.notify(f"Initial portfolio value: ${float(portfolio.portfolio_value)}")

    @staticmethod
    def show_configuration():
        # TODO: Implement this
        logger.info("Running: initial steps")
