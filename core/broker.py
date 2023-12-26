import os

from alpaca.trading import TradingClient
from kink import inject

KEY_ID = "KEY_ID"
SECRET_KEY = "SECRET_KEY"
PAPER_TRADING = "PAPER_TRADING"


@inject
class AlpacaBroker(object):
    def __init__(self):
        self.api_key = os.environ.get(KEY_ID)
        self.secret_key = os.environ.get(SECRET_KEY)
        self.paper_trading = os.environ.get(PAPER_TRADING)
        self.singleton = None

    def get_instance(self) -> TradingClient:

        if self.singleton is None:
            if self.api_key is None:
                raise ValueError(f"Required environment variable {KEY_ID} is not set.")
            if self.secret_key is None:
                raise ValueError(f"Required environment variable {SECRET_KEY} is not set.")
            if self.paper_trading.lower() == "false":
                self.singleton = TradingClient(api_key=self.api_key, secret_key=self.secret_key, paper=False)
            else:
                self.singleton = TradingClient(api_key=self.api_key, secret_key=self.secret_key, paper=True)
        return self.singleton

