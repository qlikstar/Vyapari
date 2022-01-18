import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

import pandas
import talib
from kink import di, inject

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
    2. In order to avoid false breakouts, check for volume. It MUST be higher than the recent volumes.
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
    side: str
    lower_bound: float
    upper_bound: float
    range: float


@inject
class ORBStrategy(Strategy):
    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 1000
    MOVED_DAYS = 3
    BARSET_RECORDS = 60

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40
    MAX_STOCK_WATCH_COUNT = 100
    TRAIL_PERCENT = 2.00

    def __init__(self):
        self.name = "OpeningRangeBreakoutStrategy"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.pre_stock_picks: List[ORBStock] = []
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
        self.pre_stock_picks = self._get_pre_stock_picks()

    def run(self, sleep_next_x_seconds, until_time):
        self.order_service.close_all()
        self.populate_opening_range()
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
                if self._with_high_momentum(stock):

                    # long
                    if stock.side == 'long' and stock.upper_bound < current_market_price \
                            and trade_count < ORBStrategy.MAX_NUM_STOCKS:
                        logger.info("Long: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                        no_of_shares = int(ORBStrategy.AMOUNT_PER_ORDER / current_market_price)

                        stop_loss = current_market_price - (0.5 * stock.range)
                        take_profit = current_market_price + (1.0 * stock.range)

                        self.order_service.place_bracket_order(stock.symbol, "buy", no_of_shares,
                                                               stop_loss, take_profit)
                        # self.order_service.place_trailing_bracket_order(stock.symbol, "buy", no_of_shares,
                        #                                                 ORBStrategy.TRAIL_PERCENT)
                        self.stocks_traded_today.append(stock.symbol)

                    # short
                    if stock.side == 'short' and self.order_service.is_shortable(stock.symbol) \
                            and stock.lower_bound > current_market_price \
                            and trade_count < ORBStrategy.MAX_NUM_STOCKS:
                        logger.info("Short: Current market price.. {}: ${}".format(stock.symbol, current_market_price))
                        no_of_shares = int(ORBStrategy.AMOUNT_PER_ORDER / current_market_price)

                        stop_loss = current_market_price + (1 * stock.range)
                        take_profit = current_market_price - (1.5 * stock.range)

                        self.order_service.place_bracket_order(stock.symbol, "sell", no_of_shares,
                                                               stop_loss, take_profit)

                        # self.order_service.place_trailing_bracket_order(stock.symbol, "sell", no_of_shares,
                        #                                                 ORBStrategy.TRAIL_PERCENT)
                        self.stocks_traded_today.append(stock.symbol)

    def populate_opening_range(self) -> None:
        for stock_pick in self.pre_stock_picks:
            opening_bounds = self._get_opening_bounds(stock_pick.symbol)
            if len(opening_bounds) == 2:
                lower_bound, upper_bound = opening_bounds
                o_range = round(upper_bound - lower_bound, 3)
                orb_stock = ORBStock(stock_pick.symbol, stock_pick.atr_to_price, stock_pick.side,
                                     lower_bound, upper_bound, o_range)
                self.todays_stock_picks.append(orb_stock)

        logger.info(f"Today's final stock picks: {len(self.todays_stock_picks)}")
        [logger.info(f'{stock_pick}') for stock_pick in self.todays_stock_picks]

    def _get_pre_stock_picks(self) -> List[ORBStock]:
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

            try:
                df = self._get_stock_df(stock)
                df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
                df['ATR-slope-fast'] = talib.EMA(df['ATR'], timeperiod=9)
                df['ATR-slope-slow'] = talib.EMA(df['ATR'], timeperiod=14)
                increasing_atr = df.iloc[-1]['ATR-slope-fast'] > df.iloc[-1]['ATR-slope-slow'] \
                                 and df.iloc[-5]['ATR-slope-fast'] > df.iloc[-5]['ATR-slope-slow']
                atr_to_price = round((df.iloc[-1]['ATR'] / stock_price) * 100, 3)

                df['RSI'] = talib.RSI(df['close'], timeperiod=14)
                df['RSI-slope-fast'] = talib.EMA(df['RSI'], timeperiod=9)
                df['RSI-slope-slow'] = talib.EMA(df['RSI'], timeperiod=14)
                long = df.iloc[-1]['RSI-slope-fast'] > df.iloc[-1]['RSI-slope-slow'] \
                       and df.iloc[-5]['RSI-slope-fast'] > df.iloc[-5]['RSI-slope-slow']
                short = df.iloc[-1]['RSI-slope-fast'] < df.iloc[-1]['RSI-slope-slow'] \
                        and df.iloc[-5]['RSI-slope-fast'] < df.iloc[-5]['RSI-slope-slow']

                # choose the most volatile stocks
                if increasing_atr and atr_to_price > 4 and self.order_service.is_tradable(stock) and (long or short):
                    logger.info(f'[{count + 1}/{len(from_watchlist)}] -> {stock} '
                                f'has an ATR:price ratio of {atr_to_price}%')
                    if long:
                        stock_info.append(ORBStock(stock, atr_to_price, 'long', 0, 0, 0))
                    else:
                        stock_info.append(ORBStock(stock, atr_to_price, 'short', 0, 0, 0))
            except Exception as ex:
                logger.warning(f"Could not process {stock}: {ex}")

        pre_stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        logger.info(f"Today's pre-stock picks: {len(pre_stock_picks)}")
        [logger.info(f'{stock_pick}') for stock_pick in pre_stock_picks]

        return pre_stock_picks[:ORBStrategy.MAX_STOCK_WATCH_COUNT]

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

    def _get_opening_bounds(self, symbol) -> List[float]:
        today = date.today().isoformat()
        from_time = f'{today}T09:30:00-05:00'
        until_time = f'{today}T10:15:00-05:00'
        minute_bars = self.data_service.get_bars_from(symbol, Timeframe.MIN_5, from_time, until_time)
        highs = minute_bars['high'].to_list()
        lows = minute_bars['low'].to_list()

        if len(highs) >= 2 and len(lows) >= 2:
            return [min(lows), max(highs)]
        logger.warning(f"Record count of 5 min bars is lesser than threshold for : {symbol}")
        return []

    def _with_high_momentum(self, stock) -> bool:
        symbol = stock.symbol
        raw_df = self.data_service.get_bars_limit(symbol, Timeframe.MIN_5, 14)
        df = self.vwap(raw_df)

        # volumes = raw_df['volume'].to_list()
        # volume_mean = mean(volumes[:-1])
        # if volumes[-1] > volume_mean * 2.0:

        ha_df = self.heiken_ashi(df)
        ha_green = True if ha_df.iloc[-1]['HA_Close'] > ha_df.iloc[-1]['HA_Open'] else False
        buffer = df.iloc[-1]['close'] * 0.001
        logger.info(f'{stock} -> HA Green: {ha_green}, Open : {df.iloc[-1]["open"]}, VWAP: {df.iloc[-1]["VWAP"]}')
        if ha_green and df.iloc[-1]['open'] > df.iloc[-1]['VWAP'] + buffer:
            return True
        if not ha_green and df.iloc[-1]['open'] < df.iloc[-1]['VWAP'] - buffer:
            return True
        else:
            return False

    @staticmethod
    def vwap(df):
        vol = df['volume'].values
        tp = (df['low'] + df['close'] + df['high']).div(3).values
        return df.assign(VWAP=(tp * vol).cumsum() / vol.cumsum())

    @staticmethod
    def heiken_ashi(df):
        df_ha = df.copy()
        df_ha['HA_Close'] = 0.0
        df_ha['HA_Open'] = 0.0
        for i in range(df_ha.shape[0]):
            if i > 0:
                df_ha.loc[df_ha.index[i], 'HA_Open'] = (df['open'][i - 1] + df['close'][i - 1]) / 2
            df_ha.loc[df_ha.index[i], 'HA_Close'] = (df['open'][i] + df['close'][i] + df['low'][i] + df['high'][i]) / 4
        return df_ha