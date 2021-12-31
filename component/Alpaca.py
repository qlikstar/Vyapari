import alpaca_trade_api as alpaca_api
from kink import inject


@inject
class Alpaca(object):
    def __init__(self):
        self.api = alpaca_api.REST()

    def get_api(self):
        return self.api
