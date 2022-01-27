from enum import Enum

from fmp_python.fmp import FMP, Interval
from kink import inject


class Timeframe(Enum):
    MIN_1 = "1Min"
    MIN_5 = "5Min"
    MIN_15 = "15Min"
    DAY = 'day'


@inject
class DataService(object):

    def __init__(self):
        self.api = FMP()

    def get_current_price(self, symbol) -> float:
        return self.api.get_quote_short(symbol).iloc[-1]['price']

    def get_daily_bars(self, symbol: str, limit: int):
        bars = self.api.get_historical_price(symbol, limit)[::-1]
        bars.set_index('date', inplace=True)
        return bars

    def get_intra_day_bars(self, symbol: str, interval: Interval):
        bars = self.api.get_historical_chart(symbol, interval)[::-1]
        bars.set_index('date', inplace=True)
        return bars

    def save_history(self, symbol, interval: Interval, limit: int = 252):
        pass
