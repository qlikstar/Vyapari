from enum import Enum

import alpaca_trade_api as alpaca_api
from alpaca_trade_api.entity import BarSet
from kink import inject


class Timeframe(Enum):
    MIN_1 = "1Min"
    MIN_5 = "5Min"
    MIN_15 = "15Min"
    DAY = 'day'


@inject
class DataService(object):

    def __init__(self):
        self.api = alpaca_api.REST()

    def get_current_price(self, symbol) -> float:
        return self.api.get_last_trade(symbol).price

    # TODO : get_barset has been deprecated use get_bars instead
    # self.api.get_bars('AAPL', TimeFrame.Day, start='2021-09-12', end="2021-09-21").df
    # However, this does not allow query for current date !!!
    def get_bars(self, symbol: str, timeframe: Timeframe, limit: int) -> BarSet:
        return self.api.get_barset(symbol, timeframe.value, limit).df[symbol]

    def save_history(self, symbol, timeframe: Timeframe, limit: int = 252):
        pass
