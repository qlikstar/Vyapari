import logging
from datetime import date
from pathlib import Path
from typing import List

import pandas
import talib
from attr import dataclass
from kink import di

from component.schedule import SafeScheduler, FrequencyTag
from scheduled_jobs.watchlist import WatchList
from services.data_service import DataService, Timeframe
from services.order_service import OrderService
from services.position_service import PositionService

logger = logging.getLogger(__name__)


@dataclass
class LWStock:
    symbol: str
    yesterdays_change: float
    moved: float
    weightage: float
    lw_lower_bound: float
    lw_upper_bound: float
    step: float


class LWModified(object):
    """
        Larry Williams Breakout strategy :
        https://www.whselfinvest.com/en-lu/trading-platform/free-trading-strategies/tradingsystem/56-volatility-break-out-larry-williams-free
        Will run this strategy only during the day at 8 AM
        - Check the price changes until 8AM
        - Determine the list of stocks to be traded
        - Apply Larry Williams strategy
    """

    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 1000
    MOVED_DAYS = 3
    BARSET_RECORDS = 20

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40

    def __init__(self):
        self.name = "LWBreakout"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.todays_stock_picks: List[LWStock] = []
        self.stocks_traded_today: List[str] = []

    def get_algo_name(self) -> str:
        return self.name

    def initialize(self):
        self.stocks_traded_today = []
        self.todays_stock_picks = self._get_todays_picks()
        self.order_service.await_market_open()
        self.order_service.close_all()

    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self._run_singular, sleep_next_x_seconds, until_time, FrequencyTag.MINUTELY)

    def _run_singular(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open !")
            return

        # First check if stock not already purchased
        held_stocks = [x.symbol for x in self.position_service.get_all_positions()]

        for stock in self.todays_stock_picks:
            logger.info(f"Checking {stock.symbol} to place an order ...")
            # Open new positions on stocks only if not already held or if not traded today
            if stock.symbol not in held_stocks and stock.symbol not in self.stocks_traded_today:
                current_market_price = self.data_service.get_current_price(stock.symbol)
                trade_count = len(self.stocks_traded_today)

                # long
                if stock.lw_upper_bound < current_market_price and trade_count < LWModified.MAX_NUM_STOCKS:
                    logger.info("Long: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                    no_of_shares = int(LWModified.AMOUNT_PER_ORDER / current_market_price)
                    stop_loss = current_market_price - (3 * stock.step)
                    take_profit = current_market_price + (6 * stock.step)

                    self.order_service.place_bracket_order(stock.symbol, "buy", no_of_shares, stop_loss, take_profit)
                    self.stocks_traded_today.append(stock.symbol)

                # short
                # if self.order_service.is_shortable(stock.symbol) \
                #         and stock.lw_lower_bound > current_market_price and trade_count < LWModified.MAX_NUM_STOCKS:
                #     logger.info("Short: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                #     no_of_shares = int(LWModified.AMOUNT_PER_ORDER / current_market_price)
                #     stop_loss = current_market_price + (3 * stock.step)
                #     take_profit = current_market_price - (6 * stock.step)
                #
                #     self.order_service.place_bracket_order(stock.symbol, "sell", no_of_shares, stop_loss, take_profit)
                #     self.stocks_traded_today.append(stock.symbol)

    def _get_stock_df(self, stock):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, stock + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            df = pandas.read_pickle(df_path)
        else:
            if self.order_service.is_tradable(stock):
                df = self.data_service.get_bars(stock, Timeframe.DAY, limit=LWModified.BARSET_RECORDS)
                # df['pct_change'] = round(((df['close'] - df['open']) / df['open']) * 100, 4)
                # df['net_change'] = 1 + (df['pct_change'] / 100)
                # df['cum_change'] = df['net_change'].cumprod()
                df.to_pickle(df_path)

            else:
                logger.warning('stock symbol {} is not tradable with broker'.format(stock))
                return None

        return df

    def _get_todays_picks(self) -> List[LWStock]:
        # get the best buy and strong buy stock from Nasdaq.com and sort them by the best stocks

        from_watchlist = self.watchlist.get_universe()
        stock_info = []

        for count, stock in enumerate(from_watchlist):

            df = self._get_stock_df(stock)
            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > LWModified.STOCK_MAX_PRICE or stock_price < LWModified.STOCK_MIN_PRICE:
                continue

            df = self._get_stock_df(stock)
            df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=7)
            increasing_atr = df.iloc[-1]['ATR'] > df.iloc[-2]['ATR']

            df['TEMA_5'] = talib.TEMA(df['close'], timeperiod=5)
            df['TEMA_9'] = talib.TEMA(df['close'], timeperiod=9)
            uptrend = df.iloc[-1]['TEMA_5'] > df.iloc[-1]['TEMA_9'] and df.iloc[-2]['TEMA_5'] > df.iloc[-2]['TEMA_9']

            price_open = df.iloc[-1]['open']
            price_close = df.iloc[-1]['close']
            yesterdays_change = round((price_close - price_open) / price_open * 100, 3)

            todays_record = df.iloc[-1]
            t_stock_open = todays_record['open']
            t_stock_high = todays_record['high']
            t_stock_low = todays_record['low']
            y_stock_close = todays_record['close']

            t_change = round((y_stock_close - t_stock_open) / t_stock_open * 100, 3)
            t_range = t_stock_high - t_stock_low  # yesterday's range
            step = round(t_range * 0.25, 3)

            weightage = self._calculate_weightage(yesterdays_change, t_change)
            lw_lower_bound = round(stock_price - step, 3)
            lw_upper_bound = round(stock_price + step, 3)

            if increasing_atr and uptrend:
                logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {stock} moved {yesterdays_change}% yesterday')
                stock_info.append(
                    LWStock(stock, yesterdays_change, t_change, weightage, lw_lower_bound, lw_upper_bound, step))

        biggest_movers = sorted(stock_info, key=lambda i: i.weightage, reverse=True)
        stock_picks = self._select_best(biggest_movers)
        logger.info(f'today\'s picks: {[stock_pick for stock_pick in stock_picks]}')
        return stock_picks

    @staticmethod
    def _calculate_weightage(moved: float, change_low_to_market: float):
        return moved + (change_low_to_market * 2)

    @staticmethod
    def _select_best(biggest_movers):
        return [x for x in biggest_movers if x.yesterdays_change > 3]
