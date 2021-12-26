import logging

import pandas as pd
from alpaca_trade_api.entity import BarSet

from schedules.watchlist import WatchList
from strategies.strategy import Strategy
from services.broker_service import AlpacaClient, Timeframe
from services.notification_service import NoOpNotification
from services.util import load_env_variables

logger = logging.getLogger(__name__)


class DarvasBox(object):
    INVESTMENT_PER_STOCK = 1000

    def __init__(self, backtest_days: int, start_fresh=False):
        DarvasBox._set_pandas_options()
        load_env_variables()
        self.backtest_days = backtest_days
        self.start_fresh = start_fresh  # fresh download and backtest
        self.symbols = WatchList().get_universe()[:]
        self.broker = AlpacaClient(NoOpNotification())
        self.results = {}

    def download_data(self) -> None:

        for symbol in self.symbols:
            df_path = Strategy.get_backtest_file_path(symbol)
            df_path.parent.mkdir(parents=True, exist_ok=True)

            if self.start_fresh or not df_path.exists():
                logger.info("Downloading data for {} for {} days".format(symbol, self.backtest_days))
                try:
                    if self.broker.is_tradable(symbol):
                        df: BarSet = self.broker.get_bars(symbol, Timeframe.DAY, limit=self.backtest_days)
                        df.to_pickle(df_path)
                    else:
                        logger.warning("{} is not tradable with broker".format(symbol))
                except Exception:
                    pass
            else:
                logger.warning("Data already exists for {}".format(symbol))

    def _calculate_profit_per_symbol(self, symbol):
        df_path = Strategy.get_backtest_file_path(symbol)
        df = None
        if df_path.exists():
            try:
                df = pd.read_pickle(df_path)
            except Exception as ex:
                logger.warning("exception occurred while reading pickle file {}: {}".format(df_path.name, ex))

            # df['pct_change'] = round(((df['close'] - df['open']) / df['open']) * 100, 2).shift(1).fillna(0.0)
            # df['decision'] = df['pct_change'] < DarvasBox.MIN_PERCENT_CHANGE
            #
            # # df['profit_per_share']
            # df.loc[df['decision'], 'profit_per_share'] = df['close'] - df['open']
            # df.loc[not df['decision'], 'profit_per_share'] = 0
            #
            # df['profit_amt'] = (DarvasBox.INVESTMENT_PER_STOCK / df['close']) * df['profit_per_share']
            # self.results[symbol] = pd.Series(df['profit_amt'], index=df.index)

            df = df.drop(columns=['open', 'high', 'low'])
            df_dict = df.to_dict('index')
            self.calculate(symbol, df_dict)

    def calculate(self, symbol, df_dict):
        date_with_close_prices = []
        for key, val in df_dict.items():
            date_with_close_prices.append((key, df_dict[key]['close']))

        # Get the max price of the stock until last 30 days
        # If current price greater than the max price of prev step, the stock is a qualified one
        if len(date_with_close_prices) > 30:
            baselined_max_val = max(date_with_close_prices[:-30], key=DarvasBox.max_closing_price)
            current_close_price = date_with_close_prices[-1][1]
            if current_close_price > baselined_max_val[1]:
                print("{}: Qualified stock: {}, Current price: {}"
                      .format(symbol, baselined_max_val, date_with_close_prices[-1]))

                # Check if the stock has been forming higher highs within the last 30 days, then "BUY"
                last_month_dict = date_with_close_prices[-30:]
                max_price_last_month = max(last_month_dict, key=DarvasBox.max_closing_price)
                percentage_change = (current_close_price - max_price_last_month[1]) / current_close_price
                if percentage_change > -0.06:
                    print("BUY : max price during last month: {}, current price: {}, %change: {}"
                          .format(max_price_last_month[1], current_close_price, percentage_change))
                else:
                    print("skip")

    def populate_results(self):
        for symbol in self.symbols:
            self._calculate_profit_per_symbol(symbol)
        final_df = pd.DataFrame(self.results)
        final_df['profit'] = final_df.sum(axis=1, skipna=True)
        # print("final DF", final_df)
        # print(final_df['profit'].iloc[-200:].to_json)

    @staticmethod
    def max_closing_price(a):
        return a[1]

    @staticmethod
    def _set_pandas_options():
        pd.set_option('display.max_columns', None)  # or 1000
        pd.set_option('display.max_rows', None)  # or 1000
        pd.set_option('display.max_colwidth', None)  # or 19
