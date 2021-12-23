import logging

from kink import di

from utils.broker import Broker
from utils.notification import Notification

logger = logging.getLogger(__name__)


class InitialSteps(object):
    def __init__(self):  # db, broker
        self.broker = di[Broker]
        self.notification = di[Notification]
        self.show_configuration()

    def show_portfolio_details(self):
        portfolio = self.broker.get_portfolio()
        self.notification.notify("Initial portfolio value: ${:.2f}".format(float(portfolio.portfolio_value)))

    @staticmethod
    def show_configuration():
        # TODO: Implement this
        logger.info("Running: initial steps")
