from datetime import datetime
from typing import List

import alpaca_trade_api as alpaca_api
from alpaca_trade_api.entity import Account
from kink import di, inject

from core.database import Database
from core.db_tables import AccountEntity


@inject
class AccountService(object):

    def __init__(self):
        self.api = alpaca_api.REST()
        self.db: Database = di[Database]

    def get_account_details(self) -> Account:
        account: Account = self.api.get_account()
        self.db.upsert_account(datetime.date(datetime.today()),
                               float(account.portfolio_value), float(account.portfolio_value))
        return account

    def get_portfolio_history(self) -> List[AccountEntity]:
        return self.db.get_portfolio_history(20)
