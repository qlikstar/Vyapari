import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import List, Tuple

import pandas
import talib
from kink import di

from core.schedule import SafeScheduler, FrequencyTag
from scheduled_jobs.watchlist import WatchList
from services.data_service import DataService, Timeframe
from services.order_service import OrderService
from services.position_service import PositionService
from strategies.strategy import Strategy

'''
References:
    1. https://www.youtube.com/watch?v=ULWtFOuUiHw : How To Trade OPENING RANGE BREAKOUT STRATEGY 
       And How To Select Stocks (Intraday Trading)
    2. https://www.youtube.com/watch?v=hk4d8AxbQ3A : OPENING RANGE In PRICE ACTION Trading (3 RULES That WORK)   
    2. https://www.youtube.com/watch?v=RZ_4OI_K6Aw: Python implementation 
    3. More info: https://www.google.com/amp/s/bullishbears.com/opening-range-breakout/amp/
    
Rules:
    1. when market opens, determine the range of the breakout during the first 30 min.
    This range is the breakout range.
    2. In oder to avoid false breakouts, check for volume. It MUST be higher than the recent volumes.
    3. Better chances are there if the closing price is above VWAP 
    4. Make sure Volatility range  > 18
    5. Stop Loss: Use session low as stop loss. However, 2 step Stop loss approach is better.
       a. Sell half of the stocks when the price reaches the upper limit.
       b. Hold rest of the stocks and apply Chandelier stop loss and continue moving
       c. Sell all at 12 PM
       
Steps:
    1. get the list of high volume stocks and ETFs from NASDAQ (TSLA, AAPL, QQQ etc)
    2. determine the stocks with high volatilty (using ATR)
    3. Now, at 7 AM, get the DFs and determine the Opening Range
    4. Run _singular jobs every 5 minutes to determine if the stock has crossed the upper/lowe range
    5. If it hs crossed and the volume for the duration is higher than last 5 durations, enter the trade, 
    with a trailing stop loss equal to twice the 5-min ATR  
       
    alpaca.get_barset('QQQ', "15Min", start='2022-01-03T09:00:00-05:00', until='2022-01-03T10:15:00-05:00').df
'''

logger = logging.getLogger(__name__)


@dataclass
class ORBStock:
    symbol: str
    atr_to_price: float
    lower_bound: float
    upper_bound: float
    range: float


class ORBStrategy(Strategy):
    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 1000
    MOVED_DAYS = 3
    BARSET_RECORDS = 20

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40

    def __init__(self):
        self.name = "OpeningRangeBreakoutStrategy"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.todays_stock_picks: List[ORBStock] = []
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
                    if stock.upper_bound < current_market_price and trade_count < ORBStrategy.MAX_NUM_STOCKS:
                        logger.info("Long: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                        no_of_shares = int(ORBStrategy.AMOUNT_PER_ORDER / current_market_price)
                        stop_loss = current_market_price - stock.range
                        take_profit = current_market_price + stock.range

                        self.order_service.place_bracket_order(stock.symbol, "buy", no_of_shares,
                                                               stop_loss, take_profit)
                        self.stocks_traded_today.append(stock.symbol)

                    # short
                    if self.order_service.is_shortable(stock.symbol) \
                            and stock.lower_bound > current_market_price \
                            and trade_count < ORBStrategy.MAX_NUM_STOCKS:
                        logger.info("Short: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                        no_of_shares = int(ORBStrategy.AMOUNT_PER_ORDER / current_market_price)
                        stop_loss = current_market_price + stock.range
                        take_profit = current_market_price - stock.range

                        self.order_service.place_bracket_order(stock.symbol, "sell", no_of_shares,
                                                               stop_loss, take_profit)
                        self.stocks_traded_today.append(stock.symbol)

    def _get_todays_picks(self) -> List[ORBStock]:
        # get the best buy and strong buy stock from Nasdaq.com and sort them by the best stocks

        logger.info("Downloading data ...")
        from_watchlist = self.watchlist.get_universe()
        stock_info: List[ORBStock] = []

        for count, stock in enumerate(from_watchlist):

            df = self._get_stock_df(stock)
            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > ORBStrategy.STOCK_MAX_PRICE or stock_price < ORBStrategy.STOCK_MIN_PRICE:
                continue

            df = self._get_stock_df(stock)
            df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=7)
            increasing_atr = df.iloc[-1]['ATR'] > df.iloc[-2]['ATR'] > df.iloc[-3]['ATR']
            atr_to_price = round((df.iloc[-1]['ATR'] / stock_price) * 100, 3)

            # choose the most volatile stocks
            if increasing_atr and atr_to_price > 5 and self.order_service.is_tradable(stock):
                logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {stock} has an ATR:price ratio of {atr_to_price}%')
                lower_bound, upper_bound = self._get_opening_range(stock)
                stock_info.append(ORBStock(stock, atr_to_price, lower_bound, upper_bound, upper_bound - lower_bound))

        stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        logger.info(f'Today\'s stock picks: {len(stock_picks)}')
        [logger.info(f'{stock_pick}') for stock_pick in stock_picks]

        return stock_picks

    def _get_stock_df(self, stock):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, stock + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            logger.info(f'data for {stock} exists locally')
            df = pandas.read_pickle(df_path)
        else:
            df = self.data_service.get_bars_limit(stock, Timeframe.DAY, limit=ORBStrategy.BARSET_RECORDS)
            # df['pct_change'] = round(((df['close'] - df['open']) / df['open']) * 100, 4)
            # df['net_change'] = 1 + (df['pct_change'] / 100)
            # df['cum_change'] = df['net_change'].cumprod()
            df.to_pickle(df_path)

        return df

    def _get_opening_range(self, symbol) -> Tuple[float, float]:
        today = date.today().isoformat()
        from_time = f'{today}T09:30:00-05:00'
        until_time = f'{today}T10:15:00-05:00'
        minute_bars = self.data_service.get_bars_from(symbol, Timeframe.MIN_15, from_time, until_time)
        highs = minute_bars['high'].to_list()
        lows = minute_bars['low'].to_list()
        return min(lows), max(highs)

    def _with_high_volume(self, symbol):
        minute_bars = self.data_service.get_bars_limit(symbol, Timeframe.MIN_5, 5)
        volumes = minute_bars['volume'].to_list()
        volume_mean = mean(volumes[:-1])
        return volumes[-1] > volume_mean * 2.0
