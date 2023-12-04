import logging
from typing import List

from alpaca.trading import TradeAccount
from kink import di
from pandas import DataFrame

from core.schedule import SafeScheduler, JobRunType
from universe.BarchartUniverse import BarchartUniverse
from services.account_service import AccountService
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService
from strategies.strategy import Strategy

logger = logging.getLogger(__name__)

'''
    URL: https://www.barchart.com/stocks/top-100-stocks?orderBy=weightedAlpha&orderDir=desc
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
        print(self.stock_picks_today)
        self._run_trading()

    # ''' Since this is a strict LONG TERM strategy, run it every 24 hrs '''
    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self.run_dummy, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def prep_stocks(self) -> DataFrame:
        logger.info("Downloading data ...")

        # Get universe of stocks
        hqm: DataFrame = (self.universe.get_stocks_df().sort_values(by='currentRankUsTop100', ascending=True).head(51))
        print(hqm)
        return hqm

    def _run_trading(self):
        if not self.order_service.is_market_open():
            logger.warning("Market is not open !")
            return

        held_stocks = {x.symbol: x.qty for x in self.position_service.get_all_positions()}
        # Extract unique values from the 'symbol' column while preserving order
        top_picks_today = self.stock_picks_today['symbol'].unique()

        # Liquidate the previously held stocks if they don't come in the top 50 stocks
        to_be_removed = []
        for held_stock in held_stocks.keys():
            if held_stock not in top_picks_today:
                self.order_service.market_sell(held_stock, held_stocks[held_stock])
                to_be_removed.append(held_stock)

        for stock in to_be_removed:
            del held_stocks[stock]

        if len(held_stocks) < MAX_STOCKS_TO_PURCHASE:
            no_of_stocks_to_purchase = MAX_STOCKS_TO_PURCHASE - len(held_stocks)

            stocks_to_purchase = []
            for stock in top_picks_today:
                if (stock not in held_stocks.keys()
                        and self.order_service.is_tradable(stock)
                        and len(stocks_to_purchase) < no_of_stocks_to_purchase):
                    stocks_to_purchase.append(stock)

            self.purchase_stocks(stocks_to_purchase)

        else:
            logger.info("No stocks to purchase today")

    def purchase_stocks(self, symbols: list[str]):
        account: TradeAccount = self.account_service.get_account_details()
        buying_power = float(account.buying_power) / int(account.multiplier)
        position_size_per_symbol: float = buying_power / len(symbols)

        for symbol in symbols:
            qty = position_size_per_symbol / self.data_service.get_current_price(symbol)
            self.order_service.market_buy(symbol, int(qty))

    @staticmethod
    def run_dummy():
        logger.info("Running dummy job ...")
