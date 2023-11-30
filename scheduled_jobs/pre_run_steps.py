import logging

from kink import di, inject

from services.account_service import AccountService
from services.notification_service import Notification

logger = logging.getLogger(__name__)


@inject
class PreRunSteps(object):
    def __init__(self):  # db, broker
        self.account_service: AccountService = di[AccountService]
        self.notification: Notification = di[Notification]
        self.show_configuration()

    def show_portfolio_details(self):
        portfolio = self.account_service.get_account_details()
        message = f"Initial portfolio value: ${float(portfolio.portfolio_value)}"
        logger.info(message)
        self.notification.notify(message)

    def show_configuration(self):
        # TODO: Implement this
        logger.info("Running: pre run steps ...")
