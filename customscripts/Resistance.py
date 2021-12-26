import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from alpaca_trade_api.entity import BarSet
from kink import di
from mplfinance.original_flavor import candlestick_ohlc

from strategies.strategy import Strategy
from services.broker_service import Timeframe, Broker
from services.util import load_env_variables

"""
    Resistance and Support calculation:
    https://medium.datadriveninvestor.com/how-to-detect-support-resistance-levels-and-breakout-using-python-f8b5dac42f21
"""


class Resistance(object):

    def __init__(self, symbol: str, lookback_days: int):
        Resistance._set_pandas_options()
        load_env_variables()
        self.symbol = symbol
        self.lookback_days = lookback_days
        self.broker = di[Broker]
        self.results = {}
        self.download_data(symbol)

    def download_data(self, symbol) -> None:

        df_path = Strategy.get_backtest_file_path(symbol)
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if not df_path.exists():
            print("Downloading data for {} for {} days".format(symbol, self.lookback_days))
            if self.broker.is_tradable(symbol):
                df: BarSet = self.broker.get_bars(symbol, Timeframe.DAY, limit=self.lookback_days)
                df.to_pickle(df_path)
            else:
                print("{} is not tradable with broker".format(symbol))
        else:
            print("Data already exists for {}".format(symbol))

    def populate_results(self):

        df = self._get_df(self.symbol)
        df['Date'] = df.index.strftime('%Y-%m-%d')
        df['Date'] = pd.to_datetime(df['Date'])
        df.index = df['Date']
        df['Date'] = df['Date'].apply(mpl_dates.date2num)
        df = df.loc[:, ['Date', 'open', 'high', 'low', 'close', 'volume']]

        resistances = []
        supports = []
        max_list = []
        min_list = []
        shift_res = 22
        shift_sup = 9
        for i in range(shift_res, len(df) - shift_res):
            # taking a window of 9 candles
            high_range = df['high'][i - shift_res:i + (shift_res - 1)]
            current_max = high_range.max()
            # if we find a new maximum value, empty the max_list
            if current_max not in max_list:
                max_list = []
            max_list.append(current_max)
            # if the maximum value remains the same after shifting "shift" times
            if len(max_list) == shift_res and self.is_far_from_level(current_max, resistances, df):
                resistances.append((high_range.idxmax(), current_max))

            low_range = df['low'][i - shift_sup:i + shift_sup]
            current_min = low_range.min()
            if current_min not in min_list:
                min_list = []
            min_list.append(current_min)
            if len(min_list) == shift_sup and self.is_far_from_level(current_min, supports, df):
                supports.append((low_range.idxmin(), current_min))

        print("*****  Resistances *****")
        [print(pivot[0], pivot[1]) for pivot in resistances]
        print("*****  Supports *****")
        [print(pivot[0], pivot[1]) for pivot in supports]
        self.plot_all(resistances, supports, df)

    def _get_df(self, symbol):
        df_path = Strategy.get_backtest_file_path(symbol)
        df = None
        if df_path.exists():
            try:
                df = pd.read_pickle(df_path)
            except Exception as ex:
                print("exception occurred while reading pickle file {}: {}".format(df_path.name, ex))
        return df

    @staticmethod
    def is_far_from_level(value, levels, df):
        ave = np.mean(df['high'] - df['low'])
        return np.sum([abs(value - level) < ave for _, level in levels]) == 0

    @staticmethod
    def plot_all(resistances, supports, df):
        fig, ax = plt.subplots(figsize=(16, 9))
        candlestick_ohlc(ax, df.values, width=0.6, colorup='green', colordown='red', alpha=0.8)
        date_format = mpl_dates.DateFormatter('%d %b %Y')
        ax.xaxis.set_major_formatter(date_format)

        for level in resistances:
            plt.hlines(level[1], xmin=df['Date'][level[0]], xmax=max(df['Date']), colors='blue', linestyle='--')
        for level in supports:
            plt.hlines(level[1], xmin=df['Date'][level[0]], xmax=max(df['Date']), colors='red', linestyle='--')
        plt.show()

    @staticmethod
    def _set_pandas_options():
        pd.set_option('display.max_columns', None)  # or 1000
        pd.set_option('display.max_rows', None)  # or 1000
        pd.set_option('display.max_colwidth', None)  # or 19
