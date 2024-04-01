import math
from typing import List, Dict

from alpaca.trading import TradeAccount
from kink import di
from pandas import DataFrame

from core.logger import logger
from core.schedule import SafeScheduler, JobRunType
from services.notification_service import Notification
from universe.BarchartUniverse import BarchartUniverse
from services.account_service import AccountService
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService, Position
from strategies.strategy import Strategy

'''
    Step 1: Download the top performing stocks from here:
            https://www.barchart.com/stocks/top-100-stocks?orderBy=weightedAlpha&orderDir=desc
    Step 2: Filter out the ones that are valued at less than $20
    Step 3: Select the top 30 for investing
    Step 4: Replace a stock only if it does not exist in the top 50 stocks
'''

MAX_STOCKS_TO_PURCHASE = 30


class BarchartStrategy(Strategy):

    def __init__(self):
        self.universe = di[BarchartUniverse]
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

    # ''' Since this is a strict LONG TERM strategy, run it every 24 hrs '''
    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self.run_dummy, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def prep_stocks(self) -> DataFrame:
        logger.info("Downloading data ...")

        # Get universe of stocks
        hqm: DataFrame = (self.universe.get_stocks_df().sort_values(by='currentRankUsTop100', ascending=True).head(51))
        # Print the HQM stocks
        self.show_stocks_df("HQM stocks today:\n", hqm)
        return hqm

    def _run_trading(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open !")
            return

        held_stocks: Dict[str, Position] = {pos.symbol: pos for pos in self.position_service.get_all_positions()}
        # Extract unique values from the 'symbol' column while preserving order
        top_picks_today = self.stock_picks_today['symbol'].unique()

        # Fetch the previously held stocks if they don't come in the top 50 stocks
        to_be_removed = []
        for held_stock in held_stocks.keys():
            if held_stock not in top_picks_today:
                to_be_removed.append(held_stock)

        if len(to_be_removed) > 0:

            # Liquidate the selected stocks
            for stock in to_be_removed:
                self.notify_to_sell(held_stocks[stock])
                self.order_service.market_sell(stock, int(held_stocks[stock].qty))
                del held_stocks[stock]

        else:
            logger.info("No stocks to be liquidated today")

        buffer: int = 5
        top_picks_addn = top_picks_today[:MAX_STOCKS_TO_PURCHASE + buffer]
        top_picks_final = [stock for stock in top_picks_addn if stock not in to_be_removed]
        self.rebalance_stocks(top_picks_final)

    def rebalance_stocks(self, symbols: List[str]):
        account = self.account_service.get_account_details()
        allocated_amt_per_symbol = float(account.portfolio_value) / MAX_STOCKS_TO_PURCHASE

        held_stocks = {pos.symbol: int(pos.qty) for pos in self.position_service.get_all_positions()}
        position_count = 0

        def calculate_qty_and_buy(sym: str) -> None:
            nonlocal position_count
            qty = int(allocated_amt_per_symbol / self.data_service.get_current_price(sym))
            qty_to_add = min(qty, qty - held_stocks.get(sym, 0))
            position_count += 1
            if qty_to_add > 0:
                self.order_service.market_buy(sym, int(qty_to_add))

        # Rebalance held stocks
        for symbol in held_stocks:
            if position_count > MAX_STOCKS_TO_PURCHASE:
                break
            calculate_qty_and_buy(symbol)

        # Rebalance selected symbols
        for symbol in set(symbols):
            if position_count > MAX_STOCKS_TO_PURCHASE:
                break
            if symbol not in held_stocks:
                calculate_qty_and_buy(symbol)

        logger.info("All stocks rebalanced for today")

    def purchase_stocks(self, symbols: list[str]):
        account: TradeAccount = self.account_service.get_account_details()
        buying_power = float(account.buying_power) / int(account.multiplier)
        position_size_per_symbol: float = buying_power / len(symbols)

        for symbol in symbols:
            qty = position_size_per_symbol / self.data_service.get_current_price(symbol)
            self.order_service.market_buy(symbol, int(qty))

    def show_stocks_df(self, msg: str, df: DataFrame):
        msg += "=======================================\n"
        msg += "Sym    Alpha   Rank  PrevRnk   Price  \n"
        msg += "=======================================\n"
        for index, row in df.iterrows():
            msg += f"{row['symbol']:<7}"
            msg += f"{row['weightedAlpha']:>6.2f}"
            msg += f"{row['currentRankUsTop100']:>6}"

            # Check if 'previousRank' is NaN before converting
            previous_rank = row['previousRank']
            msg += f"{int(previous_rank) if not math.isnan(previous_rank) else 'NaN':>8}"

            msg += f"{row['lastPrice']:>8.2f}"
            msg += "\n"
        msg += "=======================================\n"
        self.notification.notify(msg)

    def notify_to_sell(self, position: Position):
        msg = f"Selling {position.qty} of {position.symbol} at a total ${position.market_value} \n"

        if float(position.unrealized_pl) > 0:
            msg += f"at a PROFIT of {float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc):.2f}%)"
        else:
            msg += f"at a LOSS of {float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc):.2f}%)"
        self.notification.notify(msg)

    @staticmethod
    def run_dummy():
        logger.info("Running dummy job ...")
