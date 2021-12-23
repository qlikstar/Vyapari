from kink import di

from utils.broker import Broker


class CleanUp(object):

    def __init__(self):
        self.broker = di[Broker]

    def close_all_positions(self):
        self.broker.cancel_open_orders()
        self.broker.close_all_positions()
