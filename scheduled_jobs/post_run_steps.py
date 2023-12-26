from kink import di, inject

from core.logger import logger
from services.account_service import AccountService
from services.notification_service import Notification


@inject
class PostRunSteps(object):

    def __init__(self):
        self.account_service: AccountService = di[AccountService]
        self.notification: Notification = di[Notification]

    def show_portfolio_details(self):
        # TODO: delete data folder for today
        portfolio = self.account_service.get_account_details()
        self.notification.notify(f"Final portfolio value: ${float(portfolio.portfolio_value)}")
        logger.info("Completed: Final Steps for the day")
