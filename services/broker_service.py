import abc
import time
from datetime import datetime
from random import randint
from typing import List

from alpaca.trading import Position, TradeAccount, GetOrdersRequest, QueryOrderStatus
from alpaca.trading.client import TradingClient
from kink import di, inject
from requests import ReadTimeout

from core.logger import logger
from core.broker import AlpacaBroker
from services.notification_service import Notification


class Broker(abc.ABC):

    @abc.abstractmethod
    def get_portfolio(self):
        pass

    @abc.abstractmethod
    def get_positions(self) -> List[Position]:
        pass

    @abc.abstractmethod
    def await_market_open(self):
        pass

    @abc.abstractmethod
    def await_market_close(self):
        pass

    @abc.abstractmethod
    def get_order(self, order_id: str):
        pass

    @abc.abstractmethod
    def get_all_orders(self):
        pass

    @abc.abstractmethod
    def get_open_orders(self):
        pass

    @abc.abstractmethod
    def cancel_open_orders(self):
        pass

    @abc.abstractmethod
    def close_all_positions(self):
        pass

    @abc.abstractmethod
    def is_tradable(self, symbol: str):
        pass

    @abc.abstractmethod
    def is_market_open(self):
        pass


@inject(alias=Broker)
class AlpacaClient(Broker):

    MAX_RETRIES = 5

    def __init__(self):
        self.api: TradingClient = di[AlpacaBroker].get_instance()
        self.notification = di[Notification]
        assert self.get_portfolio() is not None

    def get_portfolio(self) -> TradeAccount:
        return self.api.get_account()

    def get_positions(self, trying=0) -> List[Position]:
        try:
            return self.api.get_all_positions()
        except ReadTimeout as rex:
            if trying < AlpacaClient.MAX_RETRIES:
                time.sleep(3)
                trying = trying + 1
                self.get_positions(trying)
                logger.info("Trying ... {} time".format(trying))
            else:
                self.notification.err_notify(f"Failed to get positions ... {rex}")

    def await_market_open(self):
        while not self.is_market_open():
            logger.info("{} waiting for market to open ... ".format(datetime.today().ctime()))
            time.sleep(60)
        logger.info("{}: Market is open ! ".format(datetime.today().ctime()))

    def await_market_close(self):
        while self.is_market_open():
            logger.info("{} waiting for market to close ... ".format(datetime.today().ctime()))
            time.sleep(60)
        logger.info("{}: Market is closed now ! ".format(datetime.today().ctime()))

    def is_tradable(self, symbol: str) -> bool:
        return self.api.get_asset(symbol).tradable

    def is_market_open(self) -> bool:
        now = datetime.today()
        military_time_now = (now.hour * 100) + now.minute
        return now.weekday() < 5 and 630 <= military_time_now < 1300

    def get_order(self, order_id: str):
        return self.api.get_order_by_id(order_id)

    def get_all_orders(self):
        return self.api.get_orders()

    def get_open_orders(self):
        return self.api.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))

    def cancel_open_orders(self):
        if self.is_market_open():
            logger.info("Closing all open orders ...")
            self.api.cancel_orders()
            time.sleep(randint(1, 3))

        else:
            logger.info("Could not cancel open orders ...Market is NOT open.. !")

    def close_all_positions(self, trying=0):
        if self.is_market_open():
            self.api.close_all_positions(True)

            time.sleep(randint(3, 7))
            if len(self.get_positions()) == 0:
                logger.info("Closed all open positions ...")
                return

            if trying < AlpacaClient.MAX_RETRIES:
                trying = trying + 1
                logger.info(f"Closing all open positions ... Trying: {trying} time")
                self.close_all_positions(trying)

            else:
                self.notification.notify("Could not close all positions ... ")
        else:
            logger.info("Positions cannot be closed ...Market is NOT open.. !")
