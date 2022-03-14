import logging
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
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
from services.talib_util import TalibUtil, Trend
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
pandas.set_option("display.max_rows", None, "display.max_columns", None)


class Target(Enum):
    INIT = "INIT"
    FIRST = "FIRST"
    TIMEOUT = "TIMEOUT"
    END = "END"


@dataclass
class SelectedStock:
    symbol: str
    atr_to_price: float
    side: str = None
    lower_bound: float = 0
    upper_bound: float = 0
    range: float = 0

    order_id: str = None
    order_price: float = 0
    order_qty: int = 0
    target: Target = Target.INIT


@inject
class ORBStrategy(Strategy):
    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 500
    BARSET_COUNT = 60

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40
    MAX_STOCK_WATCH_COUNT = 100
    OPEN_NEW_POSITIONS_UNTIL = "11:00"

    def __init__(self):
        self.name = "OpeningRangeBreakoutStrategy"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.pre_stock_picks: List[SelectedStock] = []
        self.todays_stock_picks: List[SelectedStock] = []
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
        self.pre_stock_picks = self._get_pre_stock_picks()

    def run(self, sleep_next_x_seconds, until_time):
        self.order_service.close_all()
        self.prep_stocks()
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

                # Open new positions on stocks only if not already held or if not traded today and within time
                if stock.symbol not in self.stocks_traded_today and not self._check_timeout():

                    current_market_price = self.data_service.get_current_price(stock.symbol)

                    # Get 5M DF
                    df = self.data_service.get_intra_day_bars(stock.symbol, Interval.MIN_5)
                    ha_df = TalibUtil.heikenashi(df)
                    df['EMA'] = talib.EMA(df['close'], timeperiod=9)

                    no_of_shares = int(ORBStrategy.AMOUNT_PER_ORDER / current_market_price)
                    stop_loss_margin = stock.range

                    # long
                    if ha_df.iloc[-1]['close'] > df.iloc[-1]['EMA'] \
                            and TalibUtil.get_ha_trend(ha_df) == Trend.BULL \
                            and len(self.stocks_traded_today) < ORBStrategy.MAX_NUM_STOCKS:
                        order_id = self.order_service.place_trailing_bracket_order(
                            stock.symbol, "buy", no_of_shares, stop_loss_margin)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'long'
                        self.stocks_traded_today.append(stock.symbol)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")
                        logger.info(f"{df.tail(10)}")

                    # short
                    if self.order_service.is_shortable(stock.symbol) \
                            and ha_df.iloc[-1]['close'] < df.iloc[-1]['EMA'] \
                            and TalibUtil.get_ha_trend(ha_df) == Trend.BEAR \
                            and len(self.stocks_traded_today) < ORBStrategy.MAX_NUM_STOCKS:
                        order_id = self.order_service.place_trailing_bracket_order(
                            stock.symbol, "sell", no_of_shares, stop_loss_margin)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'short'
                        self.stocks_traded_today.append(stock.symbol)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")
                        logger.info(f"{df.tail(10)}")

            # If the stocks hits the profit margin,
            else:
                # Get 5M DF
                df = self.data_service.get_intra_day_bars(stock.symbol, Interval.MIN_5)
                df['EMA'] = talib.EMA(df['close'], timeperiod=9)
                ha_df = TalibUtil.heikenashi(df)
                profit_margin = 0.8 * stock.range

                # check timeout
                if stock.target == Target.INIT and self._check_timeout():
                    logger.info(f"{stock.symbol}: Reached TIMEOUT {stock.side} target")
                    stock.target = Target.TIMEOUT

                if stock.side == "long":
                    current_high = df.iloc[-1]['high']

                    if stock.target == Target.INIT and current_high > stock.order_price + profit_margin:
                        logger.info(f"{stock.symbol}: Reached FIRST {stock.side} target")
                        stock.target = Target.FIRST

                    if (stock.target == Target.FIRST or stock.target == Target.TIMEOUT) \
                            and TalibUtil.get_ha_trend(ha_df) == Trend.BEAR \
                            and ha_df.iloc[-1]['close'] < df.iloc[-1]['EMA']:
                        logger.info(f"{stock.symbol}: Closing position ... Reached {stock.target}")
                        self.order_service.cancel_order(stock.order_id)
                        self.order_service.market_sell(stock.symbol, stock.order_qty)
                        stock.target = Target.END

                else:
                    current_low = df.iloc[-1]['low']
                    if stock.target == Target.INIT and current_low < stock.order_price - profit_margin:
                        logger.info(f"{stock.symbol}: Reached FIRST {stock.side} target")
                        stock.target = Target.FIRST

                    if (stock.target == Target.FIRST or stock.target == Target.TIMEOUT) \
                            and ha_df.iloc[-1]['close'] > df.iloc[-1]['EMA'] \
                            and TalibUtil.get_ha_trend(ha_df) == Trend.BULL:
                        logger.info(f"{stock.symbol}: Closing position ... Reached {stock.target}")
                        self.order_service.cancel_order(stock.order_id)
                        self.order_service.market_buy(stock.symbol, stock.order_qty)
                        stock.target = Target.END

    def prep_stocks(self) -> None:
        for stock_pick in self.pre_stock_picks:

            logger.info(f"Prepping for ... {stock_pick.symbol}")
            one_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_1)
            five_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_5)
            fifteen_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_15)

            opening_range = self._populate_opening_range(stock_pick.symbol, one_min_df, five_min_df, fifteen_min_df)
            if len(opening_range) == 2:
                lower_bound, upper_bound = opening_range
                range: float = abs(round(upper_bound - lower_bound, 2))

                orb_stock = SelectedStock(stock_pick.symbol, stock_pick.atr_to_price, stock_pick.side,
                                          lower_bound, upper_bound, range)
                self.todays_stock_picks.append(orb_stock)

        logger.info(f"Today's final stock picks: {len(self.todays_stock_picks)}")
        [logger.info(f'{stock_pick}') for stock_pick in self.todays_stock_picks]

    def _get_pre_stock_picks(self) -> List[SelectedStock]:
        # get the best buy and strong buy stock from Nasdaq.com and sort them by the best stocks

        logger.info("Downloading data ...")
        from_watchlist = self.watchlist.get_universe(2000000, 0.5)
        stock_info: List[SelectedStock] = []

        for count, stock in enumerate(from_watchlist):

            df = None
            try:
                df = self._get_stock_df(stock)
            except Exception as ex:
                logger.warning(f"symbol {stock} does not exist: {ex}")

            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > ORBStrategy.STOCK_MAX_PRICE or stock_price < ORBStrategy.STOCK_MIN_PRICE:
                continue

            try:
                df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=7)
                # df['ATR-slope-fast'] = talib.EMA(df['ATR'], timeperiod=9)
                # df['ATR-slope-slow'] = talib.EMA(df['ATR'], timeperiod=14)
                increasing_atr = True
                # df.iloc[-1]['ATR-slope-fast'] > df.iloc[-1]['ATR-slope-slow'] \
                # and df.iloc[-5]['ATR-slope-fast'] > df.iloc[-5]['ATR-slope-slow']
                atr_to_price = round((df.iloc[-1]['ATR'] / stock_price) * 100, 3)

                # df['RSI'] = talib.RSI(df['close'], timeperiod=14)
                # df['RSI-slope-fast'] = talib.EMA(df['RSI'], timeperiod=9)
                # df['RSI-slope-slow'] = talib.EMA(df['RSI'], timeperiod=14)

                # Open long positions for increasing RSI and short positions for decreasing RSI only
                # long = df.iloc[-1]['RSI-slope-fast'] > df.iloc[-1]['RSI-slope-slow'] \
                #        and df.iloc[-5]['RSI-slope-fast'] > df.iloc[-5]['RSI-slope-slow']
                # short = df.iloc[-1]['RSI-slope-fast'] < df.iloc[-1]['RSI-slope-slow'] \
                #         and df.iloc[-5]['RSI-slope-fast'] < df.iloc[-5]['RSI-slope-slow']

                # choose the most volatile stocks
                if increasing_atr and atr_to_price > 5 and self.order_service.is_tradable(stock):
                    logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {stock} '
                                f'has an ATR:price ratio of {atr_to_price}%')
                    stock_info.append(SelectedStock(stock, atr_to_price))
                    # if long:
                    #     stock_info.append(ORBStock(stock, atr_to_price, 'long'))
                    # else:
                    #     stock_info.append(ORBStock(stock, atr_to_price, 'short'))
            except Exception as ex:
                logger.warning(f"Could not process {stock}: {ex}")

        pre_stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        return pre_stock_picks[:ORBStrategy.MAX_STOCK_WATCH_COUNT]

    def _get_stock_df(self, symbol):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, symbol + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            logger.info(f'data for {symbol} exists locally')
            df = pandas.read_pickle(df_path)
        else:
            df = self.data_service.get_daily_bars(symbol, limit=ORBStrategy.BARSET_COUNT)
            df.to_pickle(df_path)
        return df

    # def place_smart_stop_loss(self, stock: SelectedStock) -> str:
    #     self.order_service.cancel_order(stock.order_id)
    #     qty_to_close: int = int(abs(stock.order_qty / 2))
    #     trail_price = round(stock.atr_to_price / 4, 2)
    #
    #     if stock.side == 'long':
    #         self.order_service.market_sell(stock.symbol, qty_to_close)
    #         order_id = self.order_service.place_trailing_stop_order(stock.symbol, 'sell',
    #                                                                 stock.order_qty - qty_to_close,
    #                                                                 trail_price)
    #     else:
    #         self.order_service.market_buy(stock.symbol, qty_to_close)
    #         order_id = self.order_service.place_trailing_stop_order(stock.symbol, 'buy',
    #                                                                 stock.order_qty - qty_to_close,
    #                                                                 trail_price)
    #
    #     stock.order_id = order_id
    #     stock.order_qty = stock.order_qty - qty_to_close
    #     return order_id

    @staticmethod
    def _populate_opening_range(symbol, one_min_df, five_min_df, fifteen_min_df) -> List[float]:
        today = date.today().isoformat()

        # because FMP data is received in EST
        from_time = f'{today} 09:29:00'
        until_time = f'{today} 10:00:00'

        # fix reduce the no of missing bars
        one_min_bars = one_min_df[(one_min_df.index > from_time) & (one_min_df.index <= until_time)]
        five_min_bars = five_min_df[(five_min_df.index > from_time) & (five_min_df.index <= until_time)]
        fifteen_min_bars = fifteen_min_df[(fifteen_min_df.index > from_time) & (fifteen_min_df.index <= until_time)]

        highs = one_min_bars['high'].to_list()
        highs.extend(five_min_bars['high'].to_list())
        highs.extend(fifteen_min_bars['high'].to_list())

        lows = one_min_bars['low'].to_list()
        lows.extend(five_min_bars['low'].to_list())
        lows.extend(fifteen_min_bars['low'].to_list())

        if len(highs) >= 2 and len(lows) >= 2:
            return [min(lows), max(highs)]
        logger.warning(f"Record count of 5 and 1 min bars is lesser than threshold for : {symbol}")
        return []

    def _check_timeout(self) -> bool:
        hour, minute = map(int, self.OPEN_NEW_POSITIONS_UNTIL.split(":"))
        now = datetime.now()
        times_out_at = now.replace(hour=hour, minute=minute)
        return now > times_out_at

    # @staticmethod
    # def _get_running_atr(five_min_df) -> float:
    #     df = five_min_df.tail(50)
    #     df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=30)
    #     return round(df.iloc[-1]['ATR'], 2)
