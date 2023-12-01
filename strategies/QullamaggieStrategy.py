from datetime import datetime, date
import logging
from dataclasses import dataclass
from typing import List

import pandas as pd
from kink import di
from pandas import DataFrame
from scipy.stats import stats

from core.schedule import SafeScheduler, JobRunType
from services.account_service import AccountService
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService
from strategies.strategy import Strategy
from universe.watchlist import WatchList

logger = logging.getLogger(__name__)

'''
    Inspired from Kristjan Qullamaggie: 
    https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/
    https://www.youtube.com/watch?v=WswZwmr2ebU
    https://www.youtube.com/watch?v=5p5KtVEDdN4
'''

MAX_STOCKS_TO_PURCHASE = 10


@dataclass
class QullamaggieStock:
    symbol: str
    range_low_date: datetime.date
    range_low_price: float
    range_high_date: datetime.date
    range_high_price: float
    days_since_highest_price: int
    profit_percentage: float
    tight_range_percentage: float


class QullamaggieStrategy(Strategy):

    def __init__(self):
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.data_service: DataService = di[DataService]
        self.account_service: AccountService = di[AccountService]
        self.schedule: SafeScheduler = di[SafeScheduler]

        self.stock_picks_today: DataFrame = None
        self.stocks_traded_today: List[str] = []

    def get_algo_name(self) -> str:
        return type(self).__name__

    def get_universe(self) -> None:
        pass

    def download_data(self):
        pass

    def define_buy_sell(self, data):
        pass

    def init_data(self) -> None:
        self.stock_picks_today: DataFrame = self.prep_stocks()
        # print(self.stock_picks_today)
        # self._run_trading()

    ''' Since this is a strict LONG TERM strategy, it does not need run on a smaller timeframe'''

    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self._run_trading, 60, until_time, JobRunType.STANDARD)

    def prep_stocks(self) -> DataFrame:
        logger.info("Downloading data ...")

        # Get universe from the watchlist
        from_watchlist: List[str] = self.watchlist.get_universe(2000000, 0.5)

        selected_stocks: list[QullamaggieStock] = []
        for symbol in from_watchlist:
            df = self.data_service.get_daily_bars(symbol, 100)
            qm_stock: QullamaggieStock = self.get_best_range(symbol, df)
            print(qm_stock)

            profit_range = abs(self.price_change_from_peak(df, qm_stock.range_high_date))

            if qm_stock.profit_percentage > 30 and profit_range < 12 and qm_stock.days_since_highest_price > 10:
                qm_stock.tight_range_percentage = profit_range
                selected_stocks.append(qm_stock)

        [print(stock) for stock in selected_stocks]
        df = pd.DataFrame([vars(stock) for stock in selected_stocks])
        print(df)

        self.calculate_percentile(df)

        return df

    def calculate_percentile(self, hqm: DataFrame) -> DataFrame:

        weightage_days_since_highest_price = 1
        weightage_profit_percentage = 1
        weightage_tight_range_percentage = 3

        for row in hqm.index:
            hqm.loc[row, 'days_since_highest_price Percentile'] = stats.percentileofscore(
                hqm['days_since_highest_price'], hqm.loc[row, 'days_since_highest_price']) / 100

            hqm.loc[row, 'profit_percentage Percentile'] = stats.percentileofscore(
                hqm['profit_percentage'], hqm.loc[row, 'profit_percentage']) / 100

            percentile_score = stats.percentileofscore(
                hqm['tight_range_percentage'],
                hqm.loc[row, 'tight_range_percentage']) / 100

            reversed_percentile = 1 - percentile_score
            hqm.loc[row, f'tight_range_percentage Percentile'] = reversed_percentile

        for row in hqm.index:
            # Retrieve percentile scores
            days_since_highest_price_percentile = hqm.loc[row, 'days_since_highest_price Percentile']
            profit_percentage_percentile = hqm.loc[row, 'profit_percentage Percentile']
            tight_range_percentage_percentile = hqm.loc[row, 'tight_range_percentage Percentile']

            # Calculate the overall score based on weightages
            overall_score = (
                    weightage_days_since_highest_price * days_since_highest_price_percentile +
                    weightage_profit_percentage * profit_percentage_percentile +
                    weightage_tight_range_percentage * tight_range_percentage_percentile
            )

            # Assign the overall score to the 'Score' column
            hqm.loc[row, 'HQM Score'] = overall_score

        hqm.sort_values(by='HQM Score', ascending=False, inplace=True)
        hqm_dataframe = hqm[:21]

        # Print or further manipulate the DataFrame as needed
        print(hqm_dataframe)

        return hqm_dataframe

    @staticmethod
    def _run_trading():
        print("Running trading ...")

    @staticmethod
    def get_best_range(symbol: str, df: DataFrame):
        if len(df) < 2:
            return "Not enough data to make a transaction"

        buy_date = sell_date = 0
        max_profit = 0
        min_price = df['close'].iloc[0]

        for index, row in df.iterrows():
            # Update minimum price if current low price is lower
            if row['close'] < min_price:
                min_price = row['close']
                buy_date = index

            # Update maximum profit and sell date if a better sell opportunity is found
            elif row['close'] - min_price > max_profit:
                max_profit = row['close'] - min_price
                sell_date = index

        high_date = datetime.strptime(str(sell_date), "%Y-%m-%d").date()

        return QullamaggieStock(symbol, buy_date, min_price, sell_date,
                                min_price + max_profit, (date.today() - high_date).days,
                                (max_profit / min_price) * 100, 0.0)

    @staticmethod
    def price_change_from_peak(df: DataFrame, start_date: datetime.date):
        df.index = pd.to_datetime(df.index)  # Convert the index to datetime

        # Filter DataFrame from the start date until the last date
        filtered_df = df.loc[df.index >= start_date]

        # Calculate price change in percentage
        price_change_percentage = ((filtered_df['close'].iloc[-1] - filtered_df['close'].iloc[0]) /
                                   filtered_df['close'].iloc[0]
                                   ) * 100

        return price_change_percentage
