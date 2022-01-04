import alpaca_trade_api as alpaca_api
from alpaca_trade_api.entity import Account
from kink import di, inject

from component.database import Database


@inject
class AccountService(object):

    def __init__(self):
        self.api = alpaca_api.REST()
        self.db: Database = di[Database]

    def get_account_details(self) -> Account:
        return self.api.get_account()

    def update_account_details(self):
        pass
