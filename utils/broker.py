import abc
import time
from datetime import datetime
from enum import Enum
from random import randint
from typing import List

import alpaca_trade_api as alpaca_api
from alpaca_trade_api.entity import BarSet, Position, Account, Order
from alpaca_trade_api.rest import APIError
from kink import di, inject
from requests import ReadTimeout

from utils.notification import Notification


class Timeframe(Enum):
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    DAY = 'day'


class Broker(abc.ABC):

    @abc.abstractmethod
    def get_portfolio(self):
        pass

    @abc.abstractmethod
    def get_current_price(self, symbol):
        pass

    @abc.abstractmethod
    def get_bars(self, symbol: str, timeframe: Timeframe, limit: int):
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
    def get_all_orders(self):
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
        self.orders: List[Order] = []
        assert self.get_portfolio() is not None

    def get_portfolio(self) -> Account:
        return self.api.get_account()

    def get_current_price(self, symbol) -> float:
        return self.api.get_last_trade(symbol).price

    # TODO : get_barset has been deprecated use get_bars instead
    # self.api.get_bars('AAPL', TimeFrame.Day, start='2021-09-12', end="2021-09-21").df
    # However, this does not allow query for current date !!!
    def get_bars(self, symbol: str, timeframe: Timeframe, limit: int) -> BarSet:
        return self.api.get_barset(symbol, timeframe.value, limit).df[symbol]

    def get_positions(self, trying=0) -> List[Position]:
        try:
            return self.api.list_positions()
        except ReadTimeout as rex:
            if trying < AlpacaClient.MAX_RETRIES:
                time.sleep(3)
                trying = trying + 1
                self.get_positions(trying)
                print("Trying ... {} time".format(trying))
            else:
                self.notification.notify("Failed to get positions ... {}".format(rex))

    def await_market_open(self):
        while not self.is_market_open():
            print("{} waiting for market to open ... ".format(datetime.today().ctime()))
            time.sleep(60)
        print("{}: Market is open ! ".format(datetime.today().ctime()))

    def await_market_close(self):
        while self.is_market_open():
            print("{} waiting for market to close ... ".format(datetime.today().ctime()))
            time.sleep(60)
        print("{}: Market is closed now ! ".format(datetime.today().ctime()))

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
            resp = self.api.submit_order(symbol, qty, side, "market", "day")
            print("Order submitted to {}: {} : {}".format(side, symbol, qty))
            return resp
        else:
            print("{} Order could not be placed ...Market is NOT open.. !".format(side))

    def place_bracket_order(self, symbol, side, qty, stop_loss, take_profit):
        print("Placing bracket order to {}: {} shares of {} -> ".format(side, qty, symbol))
        if self.is_market_open():
            try:
                resp = self.api.submit_order(symbol, qty, side, "market", "day",
                                             order_class="bracket",
                                             take_profit={"limit_price": take_profit},
                                             stop_loss={"stop_price": stop_loss})
                self.orders.append(resp)
            except APIError as api_error:
                self.notification.notify("Bracket order to {}: {} shares of {} could not be placed: {}"
                                         .format(side, qty, symbol, api_error))
            else:
                self.notification.notify("Bracket order to {}: {} shares of {} placed".format(side, qty, symbol))
                # return resp
        else:
            print("Order to {} could not be placed ...Market is NOT open.. !".format(side))

    def get_all_orders(self):
        for order in self.orders:
            print(f'fetching order for: {order.symbol}')
            print(self.api.get_order_by_client_order_id(order.client_order_id))

    def cancel_open_orders(self):
        if self.is_market_open():
            print("Closing all open orders ...")
            self.api.cancel_all_orders()
            time.sleep(randint(1, 3))

        else:
            print("Could not cancel open orders ...Market is NOT open.. !")

    def close_all_positions(self, trying=0):
        if self.is_market_open():
            self.get_all_orders()
            self.cancel_open_orders()
            self.api.close_all_positions()

            time.sleep(randint(3, 7))
            if len(self.get_positions()) == 0:
                print("Closed all open positions ...")
                return

            if trying < AlpacaClient.MAX_RETRIES:
                trying = trying + 1
                print(f"Closing all open positions ... Trying: {trying} time")
                self.close_all_positions(trying)

            else:
                self.notification.notify("Could not close all positions ... ")
        else:
            print("Positions cannot be closed ...Market is NOT open.. !")
