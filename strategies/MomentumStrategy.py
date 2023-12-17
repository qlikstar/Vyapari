import logging
from typing import List, Dict

from alpaca.trading import TradeAccount
from kink import di
from pandas import DataFrame
from scipy import stats

from core.schedule import SafeScheduler, JobRunType
from services.notification_service import Notification
from universe.watchlist import WatchList
from services.account_service import AccountService
from services.data_service import DataService
from services.order_service import OrderService
from services.position_service import PositionService, Position
from strategies.strategy import Strategy

logger = logging.getLogger(__name__)

'''
    Inspired from: 
    https://github.com/nickmccullum/algorithmic-trading-python/blob/master/finished_files/002_quantitative_momentum_strategy.ipynb
    https://www.youtube.com/watch?v=xfzGZB4HhEE&t=9090s
'''

MAX_STOCKS_TO_PURCHASE = 30
TIME_PERIOD_WEIGHTS = {'1Y': 1, '1M': 3, '3M': 3, '6M': 2}


class MomentumStrategy(Strategy):

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
        print(self.stock_picks_today)
        self._run_trading()

    # ''' Since this is a strict LONG TERM strategy, run it every 24 hrs '''
    def run(self, sleep_next_x_seconds, until_time):
        self.schedule.run_adhoc(self.run_dummy, sleep_next_x_seconds, until_time, JobRunType.STANDARD)

    def prep_stocks(self) -> DataFrame:
        logger.info("Downloading data ...")

        # Get universe from the watchlist
        from_watchlist: List[str] = self.watchlist.get_universe(2000000, 1.0)
        from_positions: List[str] = [pos.symbol for pos in self.position_service.get_all_positions()]
        universe: List[str] = list(set(from_watchlist + from_positions))

        # Fetch stock price change data
        hqm_base: DataFrame = self.data_service.stock_price_change(universe)

        # Filter out records where '1M' price change is greater than 150%
        hqm = hqm_base[hqm_base['1M'] <= 150]

        # Calculate return percentiles with weights
        for time_period, weight in TIME_PERIOD_WEIGHTS.items():
            hqm[f'{time_period} Return Percentile'] = stats.percentileofscore(
                hqm[time_period], hqm[time_period]) / 100 * weight

        # Calculate weighted HQM Score
        weighted_scores = hqm[[f'{time_period} Return Percentile' for time_period in TIME_PERIOD_WEIGHTS.keys()]]
        hqm['HQM Score'] = weighted_scores.sum(axis=1)

        # Sort by HQM Score and return the top 51 rows
        hqm = hqm.sort_values(by='HQM Score', ascending=False).head(51)

        # Print the HQM stocks
        self.show_stocks_df("HQM stocks today:\n", hqm)

        # Print the DataFrame
        print(hqm[['HQM Score'] + [f'{time_period} Return Percentile' for time_period in
                                   TIME_PERIOD_WEIGHTS.keys()]])

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

            # Print the stocks to be liquidated
            header_str = "Positions to be sold now:\n"
            cur_df: DataFrame = self.data_service.stock_price_change(to_be_removed)
            self.show_stocks_df(header_str, cur_df)

            # Liquidate the selected stocks
            for stock in to_be_removed:
                self.notify_to_sell(held_stocks[stock])
                self.order_service.market_sell(stock, int(held_stocks[stock].qty))
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

    def show_stocks_df(self, msg: str, df: DataFrame):
        msg += "=======================================\n"
        msg += "Symbol    1Y%Ch   6M%Ch   3M%Ch   1M%Ch\n"
        msg += "=======================================\n"
        for index, row in df.iterrows():
            msg += f"{row['symbol']:<7}  "
            for field in TIME_PERIOD_WEIGHTS.keys():
                msg += f"{row[field]:>6.2f}  "
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
