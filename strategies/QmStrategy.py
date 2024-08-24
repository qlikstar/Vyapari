from typing import List, Dict

import numpy as np
from kink import di
from pandas import DataFrame

from core.logger import logger
from core.schedule import SafeScheduler, JobRunType
from services.account_service import AccountService
from services.data_service import DataService
from services.notification_service import Notification
from services.order_service import OrderService
from services.position_service import PositionService, Position
from strategies.strategy import Strategy
from universe.watchlist import WatchList

MAX_STOCKS_TO_PURCHASE = 30
MAX_POSITION_SIZE = 30

'''
Qullamaggie Strategy:

- Filter out stocks that have moved upwards between 30-100% in the last 12 weeks
- Out of these stocks, look for stocks that have been consolidating for 2 - 8 weeks, but not falling below 20 day MA. Better if the stock does not fall below 10 day MA. And cannot fall below 50 day MA
- Open a long position, when the stock starts to break out of its consolidation, with a stop loss of 1 ATR
- Sell 1/3rd of the stock after it crosses 1 ATR.
- Now, for the remaining holding, move the stop to trailing stoploss of 1 ATR
- Finally close the position, if the price goes below 20 day MA
'''

class QmStrategy(Strategy):

    def __init__(self):
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.data_service: DataService = di[DataService]
        self.account_service: AccountService = di[AccountService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.notification: Notification = di[Notification]

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
        logger.info("Stock picks for today")
        logger.info(self.stock_picks_today)
        self._run_trading()

    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self.run_dummy, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def prep_stocks(self) -> DataFrame:
        logger.info("Downloading data ...")

        from_watchlist: List[str] = self.watchlist.get_universe(2000000, 1.0)
        from_positions: List[str] = [pos.symbol for pos in self.position_service.get_all_positions()]
        universe: List[str] = list(set(from_watchlist + from_positions))

        stock_data = [self.data_service.get_historical_data(stock, '12W') for stock in universe]
        filtered_stocks = [stock for stock, data in zip(universe, stock_data) if self.is_valid_stock(data)]
        return DataFrame({'symbol': filtered_stocks})

    def is_valid_stock(self, data):
        start_price = data['close'].iloc[0]
        end_price = data['close'].iloc[-1]
        percentage_change = ((end_price - start_price) / start_price) * 100
        if percentage_change < 30 or percentage_change > 100:
            return False

        data['20_MA'] = data['close'].rolling(window=20).mean()
        data['10_MA'] = data['close'].rolling(window=10).mean()
        data['50_MA'] = data['close'].rolling(window=50).mean()
        recent_data = data.tail(56)

        if recent_data['close'].min() < recent_data['20_MA'].min():
            return False
        # if recent_data['close'].min() < recent_data['10_MA'].min():
        #     return False
        # if recent_data['close'].min() < recent_data['50_MA'].min():
        #     return False

        return True

    def _run_trading(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open!")
            return

        held_stocks: Dict[str, Position] = {pos.symbol: pos for pos in self.position_service.get_all_positions()}
        top_picks_today = self.stock_picks_today['symbol'].unique()

        to_be_removed = [held_stock for held_stock in held_stocks if held_stock not in top_picks_today]

        if to_be_removed:
            header_str = "Positions to be sold now:\n"
            cur_df: DataFrame = self.data_service.stock_price_change(to_be_removed)
            self.show_stocks_df(header_str, cur_df)

            for stock in to_be_removed:
                self.notify_to_sell(held_stocks[stock])
                self.order_service.market_sell(stock, int(held_stocks[stock].qty))
                del held_stocks[stock]

            buffer: int = 10
            top_picks_addn = top_picks_today[:MAX_STOCKS_TO_PURCHASE + buffer]
            top_picks_final = [stock for stock in top_picks_addn if stock not in to_be_removed]
            self.rebalance_stocks(top_picks_final)
        else:
            logger.info("No stocks to be liquidated today")

        # Manage existing positions
        for stock in held_stocks.keys():
            self.manage_position(stock)

    def rebalance_stocks(self, symbols: List[str]):
        account = self.account_service.get_account_details()
        allocated_amt_per_symbol = float(account.portfolio_value) / MAX_STOCKS_TO_PURCHASE

        held_stocks = {pos.symbol: int(pos.qty) for pos in self.position_service.get_all_positions()}
        position_count = 0

        def calculate_qty_and_buy(sym: str) -> None:
            nonlocal position_count
            if position_count >= MAX_STOCKS_TO_PURCHASE:
                return

            current_price = self.data_service.get_current_price(sym)
            qty = int(allocated_amt_per_symbol / current_price)
            current_qty = held_stocks.get(sym, 0)
            qty_to_add = min(qty - current_qty, MAX_POSITION_SIZE - current_qty)

            if qty_to_add > 0:
                self.order_service.market_buy(sym, int(qty_to_add))
                position_count += 1
                held_stocks[sym] = current_qty + qty_to_add

        for symbol in held_stocks:
            calculate_qty_and_buy(symbol)

        for symbol in set(symbols):
            if symbol not in held_stocks:
                calculate_qty_and_buy(symbol)

        logger.info("All stocks rebalanced for today")

    def manage_position(self, stock):
        data = self.data_service.get_historical_data(stock, '1D')
        atr = self.calculate_atr(data)
        initial_stop_loss = self.position_service.get_stop_loss(stock)
        current_price = data['close'].iloc[-1]

        if current_price >= initial_stop_loss + atr:
            self.position_service.sell(stock, quantity=1/3)
            new_stop_loss = current_price - atr
            self.position_service.set_stop_loss(stock, new_stop_loss)
            self.notification.notify(f"Sold 1/3 of {stock} and moved stop loss to {new_stop_loss}")

        if current_price < data['20_MA'].iloc[-1]:
            self.position_service.sell(stock, all=True)
            self.notification.notify(f"Closed position in {stock} as it fell below 20 day MA")

    def calculate_atr(self, data):
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        tr = high_low.combine(high_close, max).combine(low_close, max)
        atr = tr.rolling(window=14).mean().iloc[-1]
        return atr

    def show_stocks_df(self, msg: str, df: DataFrame):
        msg += "=======================================\n"
        msg += "Symbol    1Y%Ch   6M%Ch   3M%Ch   1M%Ch\n"
        msg += "=======================================\n"
        for index, row in df.iterrows():
            msg += f"{row['symbol']:<7}  "
            for field in ['1Y', '6M', '3M', '1M']:
                msg += f"{row[field]:>6.2f}  "
            msg += "\n"
        msg += "=======================================\n"
        self.notification.notify(msg)

    def notify_to_sell(self, position: Position):
        msg = f"Selling {position.qty} of {position.symbol} at a total ${position.market_value:.2f}\n"
        if float(position.unrealized_pl) > 0:
            msg += f"at a PROFIT of {float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc):.2f}%)"
        else:
            msg += f"at a LOSS of {float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc):.2f}%)"
        self.notification.notify(msg)

    @staticmethod
    def run_dummy():
        logger.info("Running dummy job ...")