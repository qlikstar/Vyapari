import time
from typing import Dict
from kink import di
from pandas import DataFrame
from scipy import stats

from core.logger import logger
from core.schedule import SafeScheduler, JobRunType
from services.notification_service import Notification
from universe.watchlist import WatchList
from services.account_service import AccountService
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService, Position
from strategies.strategy import Strategy
from tabulate import tabulate

'''
    Step 1: Get a list of popular stocks/ETFs
    Step 2: Run the Momentum strategy 
    Step 3: Select the top 30 for investing
    Step 4: Replace a stock only if it does not exist in the top 50 stocks

    Inspired from: 
    https://github.com/nickmccullum/algorithmic-trading-python/blob/master/finished_files/002_quantitative_momentum_strategy.ipynb
    https://www.youtube.com/watch?v=xfzGZB4HhEE&t=9090s
'''

MAX_STOCKS_TO_PURCHASE = 30
TIME_PERIOD_WEIGHTS = {'6M': 3, '3M': 3, '1M': 2, '5D': -8}


class MomentumStrategy(Strategy):

    def __init__(self):
        self.watchlist = WatchList()
        self.order_service: OrderService = di[OrderService]
        self.position_service: PositionService = di[PositionService]
        self.data_service: DataService = di[DataService]
        self.account_service: AccountService = di[AccountService]
        self.schedule: SafeScheduler = di[SafeScheduler]
        self.notification: Notification = di[Notification]

        self.stock_picks_today: DataFrame = DataFrame()
        self.stocks_traded_today: list[str] = []

    def get_algo_name(self) -> str:
        return type(self).__name__

    def get_universe(self) -> None:
        pass

    def download_data(self, symbols: list[str], start_date: str, end_date: str) -> DataFrame:
        pass

    def define_buy_sell(self, data):
        pass

    def init_data(self) -> None:
        self.stock_picks_today: DataFrame = self.prep_stocks()
        tabled_stock_picks = tabulate(self.stock_picks_today, headers='keys', tablefmt='pretty')
        logger.info(f"Stock picks for today:\n{tabled_stock_picks}")
        self._run_trading()

    # ''' Since this is a strict LONG TERM strategy, run it every 24 hrs '''
    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self.run_dummy, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def prep_stocks(self) -> DataFrame:
        logger.info("Downloading data ...")

        # Get universe from the watchlist
        from_watchlist: list[str] = self.watchlist.get_universe(1000000, 0.6, price_gt=10)
        from_positions: list[str] = [pos.symbol for pos in self.position_service.get_all_positions()]
        universe: list[str] = sorted(list(set(from_watchlist + from_positions)))

        # Fetch stock price change data
        hqm_base: DataFrame = self.data_service.stock_price_change(universe)

        # Filter out the stocks that don't meet the below criteria
        hqm = hqm_base[
            (hqm_base['6M'] > hqm_base['3M']) &  # '6M' change is greater than '3M'
            (hqm_base['3M'] >= 10) &  # '3M' change is at least 10%
            (hqm_base['1M'] <= 150) &  # '1M' change is at most 150%
            (hqm_base['1M'] > 5) &  # '1M' change is more than 1%
            (hqm_base['5D'] > -25) &  # '5D' change is not less than -25%
            (hqm_base['5D'] < 30)  # '5D' change is less than 30%
            ]

        # Calculate return percentiles with weights
        for time_period, weight in TIME_PERIOD_WEIGHTS.items():
            hqm[f'{time_period} Ret. %ile'] = stats.percentileofscore(
                hqm[time_period], hqm[time_period]) / 100 * weight

            # Format the values to two decimal places
            hqm[f'{time_period} Ret. %ile'] = hqm[f'{time_period} Ret. %ile'].apply(lambda x: f'{x:.2f}')

        # Calculate weighted HQM Score
        weighted_scores = hqm[[f'{time_period} Ret. %ile' for time_period in TIME_PERIOD_WEIGHTS.keys()]]
        hqm['HQM Score'] = weighted_scores.sum(axis=1)

        # Sort by HQM Score and return the top 51 rows
        hqm = hqm.sort_values(by='HQM Score', ascending=False).head(51)

        # Print the HQM stocks
        self.show_stocks_df("HQM stocks today:\n", hqm)

        # Print the DataFrame
        logger.info(hqm[['HQM Score'] + [f'{time_period} Ret. %ile' for time_period in
                                         TIME_PERIOD_WEIGHTS.keys()]])

        return hqm

    def _run_trading(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open!")
            return

        held_stocks: Dict[str, Position] = {pos.symbol: pos for pos in self.position_service.get_all_positions()}
        top_picks_today = self.stock_picks_today['symbol'].unique()

        # Identify stocks to be sold
        to_be_removed = [held_stock for held_stock in held_stocks if held_stock not in top_picks_today]

        if to_be_removed:
            # Print the stocks to be liquidated
            header_str = "Positions to be liquidated now:\n"
            cur_df: DataFrame = self.data_service.stock_price_change(to_be_removed)
            self.show_stocks_df(header_str, cur_df)

            # Liquidate the selected stocks
            for stock in to_be_removed:
                self.notify_to_liquidate(held_stocks[stock])
                self.order_service.market_sell(stock, int(held_stocks[stock].qty))
                del held_stocks[stock]

            time.sleep(10)  # Allow sufficient time for the stocks to liquidate
            logger.info("Above stocks have been liquidated")
        else:
            logger.info("No stocks to be liquidated today")

        account = self.account_service.get_account_details()
        logger.info(f"Current Balance: ${account.buying_power}")

        buffer: int = 10
        top_picks_addn = top_picks_today[:MAX_STOCKS_TO_PURCHASE + buffer]
        top_picks_final = [stock for stock in top_picks_addn if stock not in to_be_removed]
        self.rebalance_stocks(top_picks_final)

    def rebalance_stocks(self, symbols: list[str]):
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
            qty_to_add = qty - current_qty

            if qty_to_add > 0:
                self.order_service.market_buy(sym, int(qty_to_add))
                position_count += 1
                held_stocks[sym] = current_qty + qty_to_add
                time.sleep(3)  # Allow sufficient time to purchase

        # Re-balance held stocks
        for symbol in held_stocks:
            logger.info(f"Balancing for HELD symbol: {symbol}")
            calculate_qty_and_buy(symbol)

        # Re-balance selected symbols
        for symbol in set(symbols):
            if symbol not in held_stocks:
                logger.info(f"Balancing for NEW symbol: {symbol}")
                calculate_qty_and_buy(symbol)

        logger.info("All stocks rebalanced for today")

    def show_stocks_df(self, msg: str, df: DataFrame):
        msg += "=======================================\n"
        msg += "Symbol    6M%Ch   3M%Ch   1M%Ch   5D%Ch\n"
        msg += "=======================================\n"
        for index, row in df.iterrows():
            msg += f"{row['symbol']:<7}  "
            for field in TIME_PERIOD_WEIGHTS.keys():
                msg += f"{row[field]:>6.2f}  "
            msg += "\n"
        msg += "=======================================\n"
        self.notification.notify(msg)

    def notify_to_liquidate(self, position: Position):
        msg = f"Selling {position.qty} of {position.symbol} at a total ${float(position.market_value):.2f}\n"
        if float(position.unrealized_pl) > 0:
            msg += f"at a PROFIT of {float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc):.2f}%)"
        else:
            msg += f"at a LOSS of {float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc):.2f}%)"
        self.notification.notify(msg)

    @staticmethod
    def run_dummy():
        logger.info("Running dummy job ...")
