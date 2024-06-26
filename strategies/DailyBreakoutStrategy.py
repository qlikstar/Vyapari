from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import List
from uuid import UUID

import pandas
from alpaca.trading import OrderSide
from finta import TA as talib
from fmp_python.fmp import Interval
from kink import di, inject

from core.logger import logger
from core.schedule import SafeScheduler, JobRunType
from universe.watchlist import WatchList
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService
from strategies.strategy import Strategy

'''
References:
    1. https://www.youtube.com/watch?v=exGuyBnhN_8&t=932s
    
Rules:
    1. Before market opens, get all the stocks that have been consolidating over a very narrow range say 2% / 3% 
       for a period of 14 / 21 days
    2. Now, check every hour from 8PM onwards to see if the consolidating range has broken out by the stock by 1%.
    3. If yes, enter "long" position, by placing a trailing stop loss of 2 * ATR
       
Steps:
    1. get the list of high volume stocks and ETFs from NASDAQ (TSLA, AAPL, QQQ etc)
    2. determine the stocks with high volatilty (using ATR)
    3. Now, at 7 AM, get the DFs and determine the Opening Range
    4. Run _singular jobs every 5 minutes to determine if the stock has crossed the upper/lower range
    5. If it hs crossed and the volume for the duration is higher than last 5 durations, enter the trade, 
    with a trailing stop loss equal to twice the 5-min ATR  
       
    alpaca.get_barset('QQQ', "15Min", start='2022-01-03T09:00:00-05:00', until='2022-01-03T10:15:00-05:00').df
'''


class Target(Enum):
    INIT = "INIT"
    FIRST = "FIRST"
    FINAL = "FINAL"


@dataclass
class BreakoutStock:
    symbol: str
    atr_to_price: float
    side: str = None
    lower_bound: float = 0
    upper_bound: float = 0
    running_atr: float = 0

    order_id: str = None
    order_price: float = 0
    order_qty: int = 0
    target: Target = Target.INIT


@inject
class DailyBreakoutStrategy(Strategy):
    # TODO : Move the constants to Algo config
    STOCK_MIN_PRICE = 20
    STOCK_MAX_PRICE = 500
    BARSET_RECORDS = 60

    AMOUNT_PER_ORDER = 1000
    MAX_NUM_STOCKS = 40
    MAX_STOCK_WATCH_COUNT = 100

    def __init__(self):
        self.name = "DailyBreakoutStrategy"
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.data_service: DataService = di[DataService]

        self.pre_stock_picks: List[BreakoutStock] = []
        self.todays_stock_picks: List[BreakoutStock] = []
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
        self.schedule.run_adhoc(self._run_singular, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def _run_singular(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open !")
            return

        # First check if stock not already purchased
        held_stocks = [x.symbol for x in self.position_service.get_all_positions()]

        for stock in self.todays_stock_picks:
            logger.info(f"Checking {stock.symbol} to place an order ...")
            current_market_price = self.data_service.get_current_price(stock.symbol)

            if stock.symbol not in held_stocks:

                # Open new positions on stocks only if not already held or if not traded today
                if stock.symbol not in self.stocks_traded_today:

                    # long
                    if current_market_price > stock.upper_bound + (1 * stock.running_atr) \
                            and len(self.stocks_traded_today) < DailyBreakoutStrategy.MAX_NUM_STOCKS:

                        no_of_shares = int(DailyBreakoutStrategy.AMOUNT_PER_ORDER / current_market_price)
                        order_id = self.order_service.place_trailing_bracket_order(stock.symbol, OrderSide.BUY,
                                                                                   no_of_shares, 2 * stock.running_atr)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'long'
                        self.stocks_traded_today.append(stock.symbol)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")

                    # short
                    if self.order_service.is_shortable(stock.symbol) \
                            and current_market_price < stock.lower_bound - (1 * stock.running_atr) \
                            and len(self.stocks_traded_today) < DailyBreakoutStrategy.MAX_NUM_STOCKS:

                        no_of_shares = int(DailyBreakoutStrategy.AMOUNT_PER_ORDER / current_market_price)
                        order_id = self.order_service.place_trailing_bracket_order(stock.symbol, OrderSide.SELL,
                                                                                   no_of_shares, 2 * stock.running_atr)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'short'
                        self.stocks_traded_today.append(stock.symbol)
                        logger.info(f"Placed order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")

                else:
                    # If 'long' position was opened and then stopped out due to loss, and the price goes below the
                    # lower limit, then open 'short' position now (assuming strong reversal) and
                    # vice-versa for 'short' positions

                    # Go short the previously closed 'long' positions
                    logger.info(f"{stock.symbol} was stopped out earlier and will try reversing now... ")
                    if stock.side == 'long' and self.order_service.is_shortable(stock.symbol) \
                            and current_market_price < stock.lower_bound + (1 * stock.running_atr):

                        no_of_shares = int(DailyBreakoutStrategy.AMOUNT_PER_ORDER / current_market_price)
                        order_id = self.order_service \
                            .place_trailing_bracket_order(stock.symbol, OrderSide.SELL, no_of_shares, 2 * stock.running_atr)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'short'
                        logger.info(f"Placed REVERSE order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")

                    # Go long the previously closed 'short' positions
                    if stock.side == 'short' and current_market_price > stock.upper_bound - (1 * stock.running_atr):

                        no_of_shares = int(DailyBreakoutStrategy.AMOUNT_PER_ORDER / current_market_price)
                        order_id = self.order_service.place_trailing_bracket_order(stock.symbol, OrderSide.BUY,
                                                                                   no_of_shares, 2 * stock.running_atr)

                        stock.order_id = order_id
                        stock.order_price = current_market_price
                        stock.order_qty = no_of_shares
                        stock.side = 'long'
                        logger.info(f"Placed REVERSE order for {stock.symbol}:{stock.side} at ${current_market_price}")
                        logger.info(f"Stock data : {stock}")

            # Check if the stocks hits the first limit, close half of the stocks and decrease the trailing stop by half
            # OR if the stock hits the upper limit, the position can be closed
            else:
                if stock.side == "long":
                    if stock.target == Target.INIT and \
                            current_market_price > stock.order_price + (2 * stock.running_atr):
                        logger.info(f"{stock.symbol}: Reached FIRST {stock.side} target: ${current_market_price}")
                        stock.order_id = self.place_smart_stop_loss(stock)
                        stock.target = Target.FIRST

                    if stock.target == Target.FIRST and \
                            current_market_price > stock.order_price + (4 * stock.running_atr):
                        logger.info(f"{stock.symbol}: Reached FINAL {stock.side} target: ${current_market_price}")
                        self.order_service.cancel_order(str(stock.order_id))
                        self.order_service.market_sell(stock.symbol, stock.order_qty)
                        stock.target = Target.FINAL

                else:
                    if stock.target == Target.INIT and \
                            current_market_price < stock.order_price - (2 * stock.running_atr):
                        logger.info(f"{stock.symbol}: Reached FIRST {stock.side} target: ${current_market_price}")
                        stock.order_id = self.place_smart_stop_loss(stock)
                        stock.target = Target.FIRST

                    if stock.target == Target.FIRST and \
                            current_market_price < stock.order_price - (4 * stock.running_atr):
                        logger.info(f"{stock.symbol}: Reached FINAL {stock.side} target: ${current_market_price}")
                        self.order_service.cancel_order(str(stock.order_id))
                        self.order_service.market_buy(stock.symbol, stock.order_qty)
                        stock.target = Target.FINAL

    def prep_stocks(self) -> None:
        for stock_pick in self.pre_stock_picks:

            logger.info(f"Prepping for ... {stock_pick.symbol}")
            one_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_1)
            five_min_df = self.data_service.get_intra_day_bars(stock_pick.symbol, Interval.MIN_5)

            opening_range = self._populate_opening_range(stock_pick.symbol, one_min_df, five_min_df)
            if len(opening_range) == 2:
                lower_bound, upper_bound = opening_range
                running_atr = self._get_running_atr(five_min_df)

                orb_stock = BreakoutStock(stock_pick.symbol, stock_pick.atr_to_price, stock_pick.side,
                                          lower_bound, upper_bound, running_atr)
                self.todays_stock_picks.append(orb_stock)

        logger.info(f"Today's final stock picks: {len(self.todays_stock_picks)}")
        [logger.info(f'{stock_pick}') for stock_pick in self.todays_stock_picks]

    def _get_pre_stock_picks(self) -> List[BreakoutStock]:
        # get the best buy and strong buy stock from Nasdaq.com and sort them by the best stocks

        logger.info("Downloading data ...")
        from_watchlist: List[str] = self.watchlist.get_universe(2000000, 1.0)
        stock_info: List[BreakoutStock] = []

        for count, stock in enumerate(from_watchlist):

            df = None
            try:
                df = self._get_stock_df(stock)
            except Exception as ex:
                logger.warning(f"symbol {stock} does not exist: {ex}")

            if df is None:
                continue

            stock_price = df.iloc[-1]['close']
            if stock_price > DailyBreakoutStrategy.STOCK_MAX_PRICE or stock_price < DailyBreakoutStrategy.STOCK_MIN_PRICE:
                continue

            try:
                df['ATR'] = talib(df['high'], df['low'], df['close'], timeperiod=14)
                df['ATR-slope-fast'] = talib.EMA(df['ATR'], period=9)
                df['ATR-slope-slow'] = talib.EMA(df['ATR'], period=14)
                increasing_atr = df.iloc[-1]['ATR-slope-fast'] > df.iloc[-1]['ATR-slope-slow'] \
                                 and df.iloc[-5]['ATR-slope-fast'] > df.iloc[-5]['ATR-slope-slow']
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
                    stock_info.append(BreakoutStock(stock, atr_to_price))
                    # if long:
                    #     stock_info.append(ORBStock(stock, atr_to_price, 'long'))
                    # else:
                    #     stock_info.append(ORBStock(stock, atr_to_price, 'short'))
            except Exception as ex:
                logger.warning(f"Could not process {stock}: {ex}")

        pre_stock_picks = sorted(stock_info, key=lambda i: i.atr_to_price, reverse=True)
        return pre_stock_picks[:DailyBreakoutStrategy.MAX_STOCK_WATCH_COUNT]

    def _get_stock_df(self, stock):
        data_folder = "data"
        today = date.today().isoformat()
        df_path = Path("/".join([data_folder, today, stock + ".pkl"]))
        df_path.parent.mkdir(parents=True, exist_ok=True)

        if df_path.exists():
            logger.info(f'data for {stock} exists locally')
            df = pandas.read_pickle(df_path)
        else:
            df = self.data_service.get_daily_bars(stock, limit=DailyBreakoutStrategy.BARSET_RECORDS)
            df.to_pickle(df_path)
        return df

    def place_smart_stop_loss(self, stock: BreakoutStock) -> UUID:
        self.order_service.cancel_order(stock.order_id)
        qty_to_close: int = int(abs(stock.order_qty / 2))

        if stock.side == 'long':
            self.order_service.market_sell(stock.symbol, qty_to_close)
            order_id = self.order_service.place_trailing_stop_order(stock.symbol, 'sell',
                                                                    stock.order_qty - qty_to_close,
                                                                    1 * stock.running_atr)
        else:
            self.order_service.market_buy(stock.symbol, qty_to_close)
            order_id = self.order_service.place_trailing_stop_order(stock.symbol, 'buy',
                                                                    stock.order_qty - qty_to_close,
                                                                    1 * stock.running_atr)

        stock.order_id = order_id
        stock.order_qty = stock.order_qty - qty_to_close
        return order_id

    @staticmethod
    def _populate_opening_range(symbol, one_min_df, five_min_df) -> List[float]:
        today = date.today().isoformat()

        # because FMP data is received in EST
        from_time = f'{today} 09:29:00'
        until_time = f'{today} 10:00:00'

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
        df['ATR'] = talib.ATR(df, period=30)
        return round(df.iloc[-1]['ATR'], 2)
