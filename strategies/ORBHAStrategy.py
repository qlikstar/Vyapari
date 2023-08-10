import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

import pandas
import talib
from fmp_python.fmp import Interval
from kink import di, inject

from core.schedule import SafeScheduler, FrequencyTag
from scheduled_jobs.watchlist import WatchList
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService
from services.talib_util import TalibUtil
from strategies.BaseStrategy import Strategy

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
    2. In order to avoid false breakouts, check for volume. It MUST be higher than the recent volumes.
    3. Better chances are there if the closing price is above VWAP 
    4. Make sure Volatility range  > 18
    5. Stop Loss: Use session low as stop loss. However, 2 step Stop loss approach is better.
       a. Close half of the stocks when the price reaches the upper limit.
       b. Hold rest of the stocks and apply Chandelier stop loss and continue moving
       c. Close all at 11:55 AM

Steps:
    1. get the list of high volume stocks and ETFs from NASDAQ (TSLA, AAPL, QQQ etc)
    2. determine the stocks with high volatilty (using ATR)
    3. Now, at 7 AM, get the DFs and determine the Opening Range
    4. Run _singular jobs every 5 minutes to determine if the stock has crossed the upper/lower range
    5. If it hs crossed and the volume for the duration is higher than last 5 durations, enter the trade, 
    with a trailing stop loss equal to twice the 5-min ATR  

    alpaca.get_barset('QQQ', "15Min", start='2022-01-03T09:00:00-05:00', until='2022-01-03T10:15:00-05:00').df
'''

logger = logging.getLogger(__name__)


@dataclass
class ORBStock:
    symbol: str
    atr_to_price: float
    lower_bound: float = 0
    upper_bound: float = 0
    running_atr: float = 0

    side: str = None
    order_id: str = None
    order_price: float = 0
    order_qty: int = 0


@inject
class ORBHAStrategy(Strategy):
    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 500
    BARSET_RECORDS = 60

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40
    MAX_STOCK_WATCH_COUNT = 100

    def __init__(self):
        self.name = "ORBHeikenAshiStrategy"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.pre_stock_picks: List[ORBStock] = []
        self.todays_stock_picks: List[ORBStock] = []
        self.stocks_trading_now: List[str] = []

    def get_algo_name(self) -> str:
        return type(self).__name__

    def get_universe(self) -> None:
        pass

    def download_data(self):
        pass

    def define_buy_sell(self, data):
        pass

    def init_data(self) -> None:
        self.stocks_trading_now = []
        self.pre_stock_picks = self._get_pre_stock_picks()

    def run(self, sleep_next_x_seconds, until_time):
        self.order_service.close_all()
        self.prep_stocks()
        self.schedule.run_adhoc(self._run_singular, sleep_next_x_seconds, until_time, FrequencyTag.MINUTELY)

    def _run_singular(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open !")
            return

        # First check if stock not already purchased
        held_stocks = [x.symbol for x in self.position_service.get_all_positions()]

        for stock in self.todays_stock_picks:
            logger.info(f"Checking {stock.symbol} to place an order ...")
            current_market_price = self.data_service.get_current_price(stock.symbol)

            five_min_df = self.data_service.get_intra_day_bars(stock.symbol, Interval.MIN_5)
            ha_df = TalibUtil.heikenashi(five_min_df)
            trend = self._get_ha_trend(ha_df)

            if stock.symbol not in held_stocks:

                # Open new positions on stocks only if not already held or if not traded today
                if stock.symbol not in self.stocks_trading_now:

                    # long
                    if current_market_price > stock.upper_bound and trend == "BULLISH" \
                            and len(self.stocks_trading_now) < ORBHAStrategy.MAX_NUM_STOCKS:
                        no_of_shares = int(ORBHAStrategy.AMOUNT_PER_ORDER / current_market_price)
                        order_id = self.order_service \
                            .place_trailing_bracket_order(stock.symbol, "buy", no_of_shares, 3 * stock.running_atr)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'long'
                        self.stocks_trading_now.append(stock.symbol)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")

                    # short
                    if self.order_service.is_shortable(stock.symbol) and trend == "BEARISH" \
                            and current_market_price < stock.lower_bound \
                            and len(self.stocks_trading_now) < ORBHAStrategy.MAX_NUM_STOCKS:
                        no_of_shares = int(ORBHAStrategy.AMOUNT_PER_ORDER / current_market_price)
                        order_id = self.order_service \
                            .place_trailing_bracket_order(stock.symbol, "sell", no_of_shares, 3 * stock.running_atr)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'short'
                        self.stocks_trading_now.append(stock.symbol)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")

            # Close all positions if the HA trend changes
            else:
                logger.info(f"Evaluating {stock.symbol} to close all positions ...")

                if stock.symbol in [x.symbol for x in self.position_service.get_all_positions()]:
                    if stock.side == "long" and trend == "BEARISH":
                        logger.info(f"{stock.symbol}: Trend is {trend} now... closing all positions")
                        self.order_service.cancel_order(stock.order_id)
                        self.order_service.market_sell(stock.symbol, stock.order_qty)
                        self.stocks_trading_now.remove(stock.symbol)

                    if stock.side == "short" and trend == "BULLISH":
                        logger.info(f"{stock.symbol}: Trend is {trend} now... closing all positions")
                        self.order_service.cancel_order(stock.order_id)
                        self.order_service.market_buy(stock.symbol, stock.order_qty)
                        self.stocks_trading_now.remove(stock.symbol)

    def prep_stocks(self) -> None:
        for stock_pick in self.pre_stock_picks:

            logger.info(f"Prepping for ... {stock_pick.symbol}")
            one_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_1)
            five_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_5)

            opening_range = self._populate_opening_range(stock_pick.symbol, one_min_df, five_min_df)
            if len(opening_range) == 2:
                lower_bound, upper_bound = opening_range
                running_atr = self._get_running_atr(five_min_df)

                orb_stock = ORBStock(stock_pick.symbol, stock_pick.atr_to_price, lower_bound, upper_bound, running_atr)
                self.todays_stock_picks.append(orb_stock)

        logger.info(f"Today's final stock picks: {len(self.todays_stock_picks)}")
        [logger.info(f'{stock_pick}') for stock_pick in self.todays_stock_picks]

    def _get_pre_stock_picks(self) -> List[ORBStock]:
        # get the best buy and strong buy stock from Nasdaq.com and sort them by the best stocks

        logger.info("Downloading data ...")
        from_watchlist = self.watchlist.get_universe()
        stock_info: List[ORBStock] = []

        for count, stock in enumerate(from_watchlist):

            df = None
            try:
                df = self._get_stock_df(stock)
            except Exception as ex:
                logger.warning(f"symbol {stock} does not exist: {ex}")

            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > ORBHAStrategy.STOCK_MAX_PRICE or stock_price < ORBHAStrategy.STOCK_MIN_PRICE:
                continue

            try:
                df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
                df['ATR-slope-fast'] = talib.EMA(df['ATR'], timeperiod=9)
                df['ATR-slope-slow'] = talib.EMA(df['ATR'], timeperiod=14)
                increasing_atr = df.iloc[-1]['ATR-slope-fast'] > df.iloc[-1]['ATR-slope-slow'] \
                                 and df.iloc[-5]['ATR-slope-fast'] > df.iloc[-5]['ATR-slope-slow']
                atr_to_price = round((df.iloc[-1]['ATR'] / stock_price) * 100, 3)

                # choose the most volatile stocks
                if increasing_atr and atr_to_price > 5 and self.order_service.is_tradable(stock):
                    logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {stock} '
                                f'has an ATR:price ratio of {atr_to_price}%')
                    stock_info.append(ORBStock(stock, atr_to_price))

            except Exception as ex:
                logger.warning(f"Could not process {stock}: {ex}")

        pre_stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        return pre_stock_picks[:ORBHAStrategy.MAX_STOCK_WATCH_COUNT]

    def _get_stock_df(self, stock):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, stock + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            logger.info(f'data for {stock} exists locally')
            df = pandas.read_pickle(df_path)
        else:
            df = self.data_service.get_daily_bars(stock, limit=ORBHAStrategy.BARSET_RECORDS)
            df.to_pickle(df_path)
        return df

    @staticmethod
    def _populate_opening_range(symbol, one_min_df, five_min_df) -> List[float]:
        today = date.today().isoformat()

        # because FMP data is received in EST
        from_time = f'{today} 09:29:00'
        until_time = f'{today} 10:30:00'

        # fix reduce the no of missing bars
        one_min_bars = one_min_df[(one_min_df.index > from_time) & (one_min_df.index <= until_time)]
        five_min_bars = five_min_df[(five_min_df.index > from_time) &
                                    (five_min_df.index <= until_time)]

        highs = one_min_bars['high'].to_list()
        highs.extend(five_min_bars['high'].to_list())

        lows = one_min_bars['low'].to_list()
        lows.extend(five_min_bars['low'].to_list())

        if len(highs) >= 2 and len(lows) >= 2:
            return [min(lows), max(highs)]
        logger.warning(f"Record count of 5 and 1 min bars is lesser than threshold for : {symbol}")
        return []

    @staticmethod
    def _get_running_atr(five_min_df) -> float:
        df = five_min_df.tail(50)
        df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=30)
        return round(df.iloc[-1]['ATR'], 2)

    @staticmethod
    def _get_ha_trend(ha_df) -> str:
        latest_row = ha_df.iloc[-1]

        if latest_row['open'] == latest_row['low'] and latest_row['close'] > latest_row['open']:
            return "BULLISH"
        elif latest_row['open'] == latest_row['high'] and latest_row['close'] < latest_row['open']:
            return "BEARISH"
        else:
            return "INDECISIVE"
