from kink import di

from services.order_service import OrderService


class CleanUp(object):

    def __init__(self):
        self.order_service: OrderService = di[OrderService]

    def close_all_positions(self):
        self.order_service.close_all()
