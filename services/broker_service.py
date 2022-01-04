import abc
import logging
import time
from datetime import datetime
from random import randint
from typing import List

import alpaca_trade_api as alpaca_api
from alpaca_trade_api.entity import Position, Account
from alpaca_trade_api.rest import APIError
from kink import di, inject
from requests import ReadTimeout

from services.notification_service import Notification

logger = logging.getLogger(__name__)


class Broker(abc.ABC):

    @abc.abstractmethod
    def get_portfolio(self):
        pass

    @abc.abstractmethod
    def get_current_price(self, symbol):
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
    def place_bracket_order(self, symbol, side, qty, stop_loss, take_profit):
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
        self.api = alpaca_api.REST()
        self.notification = di[Notification]
        assert self.get_portfolio() is not None

    def get_portfolio(self) -> Account:
        return self.api.get_account()

    def get_current_price(self, symbol) -> float:
        return self.api.get_last_trade(symbol).price

    def get_positions(self, trying=0) -> List[Position]:
        try:
            return self.api.list_positions()
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

    def market_buy(self, symbol, qty):
        return self._place_market_order(symbol, qty, "buy")

    def market_sell(self, symbol, qty):
        return self._place_market_order(symbol, qty, "buy")

    def _place_market_order(self, symbol, qty, side):
        if self.is_market_open():
            try:
                logger.info("Placing order to {}: {} : {}".format(side, symbol, qty))
                return self.api.submit_order(symbol, qty, side, "market", "day")
            except APIError as api_error:
                self.notification.err_notify(f"Order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
        else:
            logger.info(f"{side} Order could not be placed ...Market is NOT open.. !")

    def place_bracket_order(self, symbol, side, qty, stop_loss, take_profit):
        logger.info("Placing bracket order to {}: {} shares of {} -> ".format(side, qty, symbol))
        if self.is_market_open():
            try:
                order = self.api.submit_order(symbol, qty, side, "market", "day",
                                              order_class="bracket",
                                              take_profit={"limit_price": take_profit},
                                              stop_loss={"stop_price": stop_loss})

                self.notification.notify("Bracket order to {}: {} shares of {} placed".format(side, qty, symbol))
                return order
            except APIError as api_error:
                self.notification.err_notify(f"Bracket order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing bracket order: {ex}")
                self.notification.err_notify(f"Error while placing bracket order: {ex}")

        else:
            logger.info("Order to {} could not be placed ...Market is NOT open.. !".format(side))

    def get_order(self, order_id: str):
        return self.api.get_order(order_id)

    def get_all_orders(self):
        return self.api.list_orders(status='all')

    def get_open_orders(self):
        return self.api.list_orders(status='open')

    def cancel_open_orders(self):
        if self.is_market_open():
            logger.info("Closing all open orders ...")
            self.api.cancel_all_orders()
            time.sleep(randint(1, 3))

        else:
            logger.info("Could not cancel open orders ...Market is NOT open.. !")

    def close_all_positions(self, trying=0):
        if self.is_market_open():
            self.cancel_open_orders()
            self.api.close_all_positions()

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
