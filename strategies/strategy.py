from abc import ABC, abstractmethod
from typing import List, Dict
import pandas as pd
import numpy as np
import logging

class Strategy(ABC):
    DATA = "data"
    logger = logging.getLogger(__name__)

    @abstractmethod
    def init_data(self):
        pass

    @abstractmethod
    def run(self, sleep_next_x_seconds: int, until_time: str):
        pass

    @abstractmethod
    def get_algo_name(self) -> str:
        pass

    @abstractmethod
    def get_universe(self) -> List[str]:
        pass

    @abstractmethod
    def download_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def define_buy_sell(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

    def backtest(self, symbols: List[str], start_date: str, end_date: str) -> Dict:
        data = self.download_data(symbols, start_date, end_date)
        signals = self.define_buy_sell(data)
        return self.calculate_performance(signals)

    def calculate_performance(self, signals: pd.DataFrame) -> Dict:
        signals['strategy_returns'] = signals['position'].shift(1) * signals['returns']
        signals['cumulative_returns'] = (1 + signals['strategy_returns']).cumprod()

        cagr = self.calculate_cagr(signals)
        sortino_ratio = self.calculate_sortino_ratio(signals)

        performance = {
            'CAGR': cagr,
            'Sortino Ratio': sortino_ratio,
            'Final Portfolio Value': signals['cumulative_returns'].iloc[-1]
        }
        return performance

    def calculate_cagr(self, signals: pd.DataFrame) -> float:
        years = (signals.index[-1] - signals.index[0]).days / 365.25
        cagr = (signals['cumulative_returns'].iloc[-1]) ** (1 / years) - 1
        return cagr

    def calculate_sortino_ratio(self, signals: pd.DataFrame) -> float:
        downside_returns = signals.loc[signals['strategy_returns'] < 0, 'strategy_returns']
        expected_return = signals['strategy_returns'].mean()
        downside_deviation = downside_returns.std()

        sortino_ratio = expected_return / downside_deviation
        return sortino_ratio

    # @staticmethod
    # def get_backtest_file_path(symbol) -> Path:
    #     return Path("/".join([Strategy.DATA, "back-test", symbol + ".pkl"]))