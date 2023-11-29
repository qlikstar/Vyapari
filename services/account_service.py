from datetime import datetime
from typing import List

from alpaca.trading import TradeAccount
from alpaca.trading.client import TradingClient
from kink import di, inject

from core.broker import AlpacaBroker
from core.database import Database
from core.db_tables import AccountEntity


@inject
class AccountService(object):

    def __init__(self):
        self.api: TradingClient = di[AlpacaBroker].get_instance()
        self.db: Database = di[Database]

    def get_account_details(self) -> TradeAccount:
        account: TradeAccount = self.api.get_account()
        self.db.upsert_account(datetime.date(datetime.today()),
                               float(account.portfolio_value), float(account.portfolio_value))
        return account

    def get_portfolio_history(self) -> List[AccountEntity]:
        return self.db.get_portfolio_history(20)
