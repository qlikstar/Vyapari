import logging
from datetime import date
from pathlib import Path
from statistics import mean
from typing import List

import pandas
import talib
from attr import dataclass
from kink import di

from core.schedule import SafeScheduler, FrequencyTag
from scheduled_jobs.watchlist import WatchList
from services.data_service import DataService, Timeframe
from services.order_service import OrderService
from services.position_service import PositionService

logger = logging.getLogger(__name__)


@dataclass
class LWStock:
    symbol: str
    y_change: float
    atr_to_price: float
    lw_lower_bound: float
    lw_upper_bound: float
    step: float


class LWBreakout(object):
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
    BARSET_RECORDS = 30

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40
    MAX_STOCK_WATCH_COUNT = 100

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

    def init_data(self) -> None:
        self.stocks_traded_today = []
        self.todays_stock_picks = self._get_todays_picks()

    def run(self, sleep_next_x_seconds, until_time):
        self.order_service.close_all()
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

                # Enter the position only on high volume
                if self._with_high_volume(stock.symbol):

                    # long
                    if stock.lw_upper_bound < current_market_price and trade_count < LWBreakout.MAX_NUM_STOCKS:
                        logger.info("Long: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                        no_of_shares = int(LWBreakout.AMOUNT_PER_ORDER / current_market_price)
                        stop_loss = current_market_price - (2 * stock.step)
                        take_profit = current_market_price + (3 * stock.step)

                        self.order_service.place_bracket_order(stock.symbol, "buy", no_of_shares,
                                                               stop_loss, take_profit)
                        self.stocks_traded_today.append(stock.symbol)

                    # short
                    if self.order_service.is_shortable(stock.symbol) \
                            and stock.lw_lower_bound > current_market_price and trade_count < LWBreakout.MAX_NUM_STOCKS:
                        logger.info("Short: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                        no_of_shares = int(LWBreakout.AMOUNT_PER_ORDER / current_market_price)
                        stop_loss = current_market_price + (2 * stock.step)
                        take_profit = current_market_price - (3 * stock.step)

                        self.order_service.place_bracket_order(stock.symbol, "sell", no_of_shares,
                                                               stop_loss, take_profit)
                        self.stocks_traded_today.append(stock.symbol)

    def _get_todays_picks(self) -> List[LWStock]:
        # get the best buy and strong buy stock from Nasdaq.com and sort them by the best stocks

        logger.info("Downloading data ...")
        from_watchlist = self.watchlist.get_universe()
        stock_info: List[LWStock] = []

        for count, stock in enumerate(from_watchlist):

            df = self._get_stock_df(stock)
            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > LWBreakout.STOCK_MAX_PRICE or stock_price < LWBreakout.STOCK_MIN_PRICE:
                continue

            df = self._get_stock_df(stock)

            df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=7)
            df['ATR-slope-fast'] = talib.EMA(df['ATR'], timeperiod=5)
            df['ATR-slope-slow'] = talib.EMA(df['ATR'], timeperiod=9)
            increasing_atr: bool = df.iloc[-1]['ATR-slope-fast'] > df.iloc[-1]['ATR-slope-slow'] \
                                   and df.iloc[-3]['ATR-slope-fast'] > df.iloc[-3]['ATR-slope-slow']
            atr_to_price = round((df.iloc[-1]['ATR'] / stock_price) * 100, 3)

            yesterdays_record = df.iloc[-1]
            y_stock_open = yesterdays_record['open']
            y_stock_high = yesterdays_record['high']
            y_stock_low = yesterdays_record['low']
            y_stock_close = yesterdays_record['close']

            y_change = round((y_stock_close - y_stock_open) / y_stock_open * 100, 3)
            y_range = y_stock_high - y_stock_low  # yesterday's range
            step = round(y_range * 0.25, 3)

            lw_lower_bound = round(stock_price - step)
            lw_upper_bound = round(stock_price + step)

            # choose the most volatile stocks
            if increasing_atr and atr_to_price > 5 and self.order_service.is_tradable(stock):
                logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {stock} has an ATR:price ratio of {atr_to_price}%')
                stock_info.append(
                    LWStock(stock, y_change, atr_to_price, lw_lower_bound, lw_upper_bound, step))

        stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        logger.info(f'Today\'s stock picks: {len(stock_picks)}')
        [logger.info(f'{stock_pick}') for stock_pick in stock_picks]

        return stock_picks[:LWBreakout.MAX_STOCK_WATCH_COUNT]

    def _get_stock_df(self, stock):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, stock + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            logger.info(f'data for {stock} exists locally')
            df = pandas.read_pickle(df_path)
        else:
            df = self.data_service.get_bars_limit(stock, Timeframe.DAY, limit=LWBreakout.BARSET_RECORDS)
            # df['pct_change'] = round(((df['close'] - df['open']) / df['open']) * 100, 4)
            # df['net_change'] = 1 + (df['pct_change'] / 100)
            # df['cum_change'] = df['net_change'].cumprod()
            df.to_pickle(df_path)

        return df

    def _with_high_volume(self, symbol):
        minute_bars = self.data_service.get_bars_limit(symbol, Timeframe.MIN_5, 5)
        volumes = minute_bars['volume'].to_list()
        volume_mean = mean(volumes[:-1])
        return volumes[-1] > volume_mean * 2.0
