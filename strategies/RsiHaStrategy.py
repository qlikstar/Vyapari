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
    1. https://www.youtube.com/watch?v=9NG0hnwO70g
    
Steps:
    1. Determine the most volatile stocks and with high volume
    2. Check for the 20 day EMA
    3. if current price > 20 EMA, place long. If current price < 20 EMA place short
    
    4. Read 1m / 5m candle sticks and convert it to Heiken Ashi Bars
    5. Calculate the 9 period EMA for every bar 
    5. Determine the 14 period RSI
    6. If the RSI > 70 and signal = "short", track the symbol actively
       a. Place an order when the HA candle is "RED" and closes below the 9 period EMA
       b. Stop loss = max (HA highs for last 7 periods)
       c. take profit: 2 X stop loss
    7. Or if the RSI < 30 and signal = "long", track symbol actively
       a. Place an order when the HA candle is "GREEN" and closes above the 9 period EMA
       b. Stop loss = min (HA lows for last 7 periods)
       c. take profit: 2 X stop loss
'''

logger = logging.getLogger(__name__)
pandas.set_option("display.max_rows", None, "display.max_columns", None)

@dataclass
class SelectedStock:
    symbol: str
    atr_to_price: float
    side: str = None
    tracking: bool = False


@inject
class RsiHaStrategy(Strategy):
    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 500
    BARSET_COUNT = 30

    AMOUNT_PER_ORDER = 4000
    MAX_HELD_STOCKS = 10
    MAX_STOCK_WATCH_COUNT = 200

    def __init__(self):
        self.name = "RSI Heiken Ashi EMA Strategy"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.todays_stock_picks: List[SelectedStock] = []
        self.stocks_tracking: List[str] = []

    def get_algo_name(self) -> str:
        return type(self).__name__

    def get_universe(self) -> None:
        pass

    def download_data(self):
        pass

    def define_buy_sell(self, data):
        pass

    def init_data(self) -> None:
        self.todays_stock_picks: List[SelectedStock] = self._get_todays_stock_picks()

    def run(self, sleep_next_x_seconds, until_time):
        # self.order_service.close_all()
        self.schedule.run_adhoc(self._run_singular, 300, until_time, FrequencyTag.FIVE_MINUTELY)

    def _run_singular(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open !")
            return

        # First check if stock not already purchased
        held_stocks = [x.symbol for x in self.position_service.get_all_positions()]

        for stock in self.todays_stock_picks:
            logger.info(f"Checking {stock.symbol} to place an order ...")

            if stock.symbol not in held_stocks:

                # Get 5M DF
                df = self.data_service.get_intra_day_bars(stock.symbol, Interval.MIN_5)

                ha_df = TalibUtil.heikenashi(df)
                trend: str = self._get_ha_trend(ha_df)

                df['EMA'] = talib.EMA(df['close'], timeperiod=14)
                df['RSI'] = talib.RSI(df['close'], timeperiod=14)
                df['RSI-slope-fast'] = talib.EMA(df['RSI'], timeperiod=9)
                df['RSI-slope-slow'] = talib.EMA(df['RSI'], timeperiod=14)

                if stock.side == "long":
                    # Set tracking to True if satisfied
                    if df.iloc[-1]['RSI'] < 30 and df.iloc[-1]['RSI-slope-fast'] < df.iloc[-1]['RSI-slope-slow']:
                        stock.tracking = True

                    if stock.tracking and trend == "BULLISH" and ha_df.iloc[-1]['close'] > df.iloc[-1]['EMA']:
                        current_market_price = self.data_service.get_current_price(stock.symbol)
                        no_of_shares = int(RsiHaStrategy.AMOUNT_PER_ORDER / current_market_price)

                        stop_loss = min(list(ha_df['low'][:-7]))
                        take_profit = current_market_price + (2 * (current_market_price - stop_loss))
                        self.order_service.place_bracket_order(stock.symbol, "buy", no_of_shares, stop_loss,
                                                               take_profit)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")
                        logger.info(f"{ha_df.tail(10)}")
                        stock.tracking = False

                if stock.side == "short" and self.order_service.is_shortable(stock.symbol):
                    # Set tracking to True if satisfied
                    if df.iloc[-1]['RSI'] > 70 and df.iloc[-1]['RSI-slope-fast'] > df.iloc[-1]['RSI-slope-slow']:
                        stock.tracking = True

                    if stock.tracking and trend == "BEARISH" and ha_df.iloc[-1]['close'] < df.iloc[-1]['EMA']:
                        current_market_price = self.data_service.get_current_price(stock.symbol)
                        no_of_shares = int(RsiHaStrategy.AMOUNT_PER_ORDER / current_market_price)

                        stop_loss = max(list(ha_df['high'][:-7]))
                        take_profit = current_market_price - (2 * (stop_loss - current_market_price))
                        self.order_service.place_bracket_order(stock.symbol, "sell", no_of_shares, stop_loss,
                                                               take_profit)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")
                        logger.info(f"{ha_df.tail(10)}")
                        stock.tracking = False

    def _get_todays_stock_picks(self) -> List[SelectedStock]:

        logger.info("Downloading data ...")
        from_watchlist = self.watchlist.get_universe(2000000, 1.0)
        stock_info: List[SelectedStock] = []

        for count, symbol in enumerate(from_watchlist):

            df = None
            try:
                df = self._get_daily_stock_df(symbol)
            except Exception as ex:
                logger.warning(f"symbol {symbol} does not exist: {ex}")

            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > RsiHaStrategy.STOCK_MAX_PRICE or stock_price < RsiHaStrategy.STOCK_MIN_PRICE:
                continue

            try:
                df['EMA'] = talib.EMA(df['close'], timeperiod=20)
                df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=7)
                atr_to_price = round((df.iloc[-1]['ATR'] / stock_price) * 100, 3)

                # Open long positions for increasing RSI and short positions for decreasing RSI only
                long = df.iloc[-1]['close'] > df.iloc[-1]['EMA']
                short = df.iloc[-1]['close'] < df.iloc[-1]['EMA']

                # choose the most volatile stocks
                if atr_to_price > 3 and self.order_service.is_tradable(symbol):
                    logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {symbol} '
                                f'has an ATR:price ratio of {atr_to_price}%')
                    if long:
                        stock_info.append(SelectedStock(symbol, atr_to_price, 'long'))
                    if short:
                        stock_info.append(SelectedStock(symbol, atr_to_price, 'short'))

            except Exception as ex:
                logger.warning(f"Could not process {symbol}: {ex}")

        pre_stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        todays_picks = pre_stock_picks[:RsiHaStrategy.MAX_STOCK_WATCH_COUNT]

        logger.info("Today's picks:")
        [logger.info(s) for s in todays_picks]
        return todays_picks

    def _get_daily_stock_df(self, symbol):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, symbol + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            logger.info(f'data for {symbol} exists locally')
            df = pandas.read_pickle(df_path)
        else:
            df = self.data_service.get_daily_bars(symbol, limit=RsiHaStrategy.BARSET_COUNT)
            df.to_pickle(df_path)
        return df

    @staticmethod
    def _get_ha_trend(ha_df) -> str:
        latest_row = ha_df.iloc[-1]

        if latest_row['open'] == latest_row['low'] and latest_row['close'] > latest_row['open']:
            return "BULLISH"
        elif latest_row['open'] == latest_row['high'] and latest_row['close'] < latest_row['open']:
            return "BEARISH"
        else:
            return "INDECISIVE"
