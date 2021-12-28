import logging
from typing import List

from alpaca_trade_api.entity import Order
from kink import inject, di

from dao.order import create_order, update_order, get_open_orders
from services.broker_service import Broker

logger = logging.getLogger(__name__)


@inject
class OrderService(object):

    def __init__(self):
        self.broker: Broker = di[Broker]

    def save_order(self, order: Order):
        order_qty = self._check_float(order.qty)
        trail_percent = self._check_float(order.trail_percent)
        trail_price = self._check_float(order.trail_price)
        stop_price = self._check_float(order.stop_price)
        filled_avg_price = self._check_float(order.filled_avg_price)
        filled_qty = self._check_float(order.filled_qty)
        hwm = self._check_float(order.hwm)
        limit_price = self._check_float(order.limit_price)

        create_order(order.id, order.id, order.symbol, order.side, order_qty, order.time_in_force,
                     order.order_class, order.type, trail_percent, trail_price, stop_price, stop_price,
                     filled_avg_price, filled_qty, hwm, limit_price, order.replaced_by, order.extended_hours,
                     order.status, order.failed_at, order.filled_at, order.canceled_at, order.expired_at,
                     order.replaced_at, order.submitted_at, order.created_at, order.updated_at)

        if order.legs is not None:
            for leg in order.legs:
                order_qty = self._check_float(leg.qty)
                trail_percent = self._check_float(leg.trail_percent)
                trail_price = self._check_float(leg.trail_price)
                stop_price = self._check_float(leg.stop_price)
                filled_avg_price = self._check_float(leg.filled_avg_price)
                filled_qty = self._check_float(leg.filled_qty)
                hwm = self._check_float(leg.hwm)
                limit_price = self._check_float(leg.limit_price)

                create_order(leg.id, order.id, leg.symbol, leg.side, order_qty, leg.time_in_force,
                             leg.order_class, leg.type, trail_percent, trail_price, stop_price, stop_price,
                             filled_avg_price, filled_qty, hwm, limit_price, leg.replaced_by, leg.extended_hours,
                             leg.status, leg.failed_at, leg.filled_at, leg.canceled_at, leg.expired_at, leg.replaced_at,
                             leg.submitted_at, leg.created_at, leg.updated_at)

        logger.info(f"Saved order id: {order.id}")

    def update_saved_order(self, order_id: str):
        order = self.broker.get_order(order_id)
        updated_stop_price = self._check_float(order.stop_price)
        filled_avg_price = self._check_float(order.filled_avg_price)
        filled_qty = self._check_float(order.filled_qty)
        hwm = self._check_float(order.hwm)
        update_order(order_id, updated_stop_price, filled_avg_price, filled_qty, hwm, order.replaced_by,
                     order.extended_hours, order.status, order.failed_at, order.filled_at, order.canceled_at,
                     order.expired_at, order.replaced_at)

        logger.info(f"Updated order id: {order.id}")

    def get_all_orders(self) -> List[Order]:
        return self.broker.get_all_orders()

    def get_open_orders(self) -> List[Order]:
        result = []
        for order in get_open_orders():
            result.append(self.broker.get_order(order.id))
        return result

    @staticmethod
    def _check_float(value):
        return 0.00 if value is None else float(value)
