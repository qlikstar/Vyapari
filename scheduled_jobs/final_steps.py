import logging

from kink import di

from services.broker_service import Broker
from services.notification_service import Notification

logger = logging.getLogger(__name__)


class FinalSteps(object):

    def __init__(self):  # db, broker
        self.broker = di[Broker]
        self.notification = di[Notification]

    def show_portfolio_details(self):
        # TODO: delete data folder for today
        portfolio = self.broker.get_portfolio()
        self.notification.notify("Final portfolio value: ${:.2f}".format(float(portfolio.portfolio_value)))
        logger.info("Completed: Final Steps")
