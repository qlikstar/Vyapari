import matplotlib.pyplot as plt
import pandas as pd
from alpaca_trade_api.entity import BarSet
from kink import di

from strategies.strategy import Strategy
from utils.broker import Timeframe, Broker
from utils.util import load_env_variables


class DarvasBox(object):

    def __init__(self, symbol: str, lookback_days: int):
        DarvasBox._set_pandas_options()
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

        self._get_support_resistance(self.symbol)
        final_df = pd.DataFrame(self.results)
        final_df['profit'] = final_df.sum(axis=1, skipna=True)
        # print("final DF", final_df)
        # print(final_df['profit'].iloc[-200:].to_json)

    def _get_support_resistance(self, symbol):
        df_path = Strategy.get_backtest_file_path(symbol)
        df = None
        if df_path.exists():
            try:
                df = pd.read_pickle(df_path)
            except Exception as ex:
                print("exception occurred while reading pickle file {}: {}".format(df_path.name, ex))

            df['high'].plot(label="high")
            print(df)
            pivots = []
            dates = []
            counter = 0
            last_pivot = 0

            range = [0] * 10
            date_range = [0] * 10
            result = []
            time_delta = pd.to_timedelta(30, "days")

            for i in df.index:
                current_max = max(range, default=0)
                value = round(df['high'][i], 2)

                range = range[1:9]
                range.append(value)
                date_range = date_range[1:9]
                date_range.append(i)

                if current_max == max(range, default=0):
                    counter += 1
                else:
                    counter = 0

                if counter == 5:
                    last_pivot = current_max
                    date_loc = range.index(last_pivot)
                    last_date = date_range[date_loc]
                    pivots.append(last_pivot)
                    dates.append(last_date)
                    result.append((last_date, last_pivot))
            print(result)

            for indres in result:
                print("Pivot point -> ", indres)
                plt.plot_date([indres[0], indres[0] + time_delta],
                              [indres[1], indres[1]], linestyle="-", linewidth=2, marker=",")
            plt.show()

    @staticmethod
    def _set_pandas_options():
        pd.set_option('display.max_columns', None)  # or 1000
        pd.set_option('display.max_rows', None)  # or 1000
        pd.set_option('display.max_colwidth', None)  # or 19
